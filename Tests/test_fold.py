"""Independent reference witnesses for strict, atomic ordered state transitions."""
import unittest

from spl_compiler.checker import check_schedule as check
from spl_compiler.evaluator import evaluate
from spl_compiler.model import SPLException
from spl_compiler.parser import parse


def schedule(body):
    return 'schedule Fold language "spl/0.1-draft" core "spl-core/0.1-draft" schema "spl-data/0.1-draft" {' + body + '}'


class FoldTests(unittest.TestCase):
    def run_source(self, body, inputs=None):
        return evaluate(check(parse(schedule(body))), inputs or {}, {})

    def test_plain_order_and_empty_initial(self):
        out = self.run_source('define x = fold [1,2,3] from 0 with s,e { yield s * 10 + e; }; emit "x" = x;')
        self.assertEqual(out.to_dict()["emissions"]["x"], "123")
        empty = self.run_source('input xs:List<Int>; define x = fold xs from 19 with s,e { yield s+e; }; emit "x"=x;', {"xs": []})
        self.assertEqual(empty.to_dict()["emissions"]["x"], "19")

    def test_initial_failure_precedes_source_and_steps(self):
        out = self.run_source('input xs:List<Ratio>; define x = fold xs from 1.0/0.0 with s,e { require false else "STEP"; yield s+e; }; emit "x"=x;', {"xs": []})
        self.assertEqual(out.diagnostics[0]["code"], "DIVISION_BY_ZERO")
        self.assertFalse(any(t["kind"] == "fold_step" for t in out.trace))

    def test_step_failure_stops_later_and_discards_outputs(self):
        out = self.run_source('opening bal:Int from "balance"; define x = fold [1,2,3] from bal with s,e { require e != 2 else "STOP"; yield s+e; }; closing bal=x; emit "x"=x;'.replace('opening bal:Int from "balance";', 'define bal=0;').replace('closing bal=x;', ''))
        self.assertEqual(out.status, "blocked")
        self.assertEqual(out.emissions, {})
        steps = [t for t in out.trace if t["kind"] == "fold_step"]
        self.assertEqual(len(steps), 2)
        self.assertEqual(steps[0]["state_before"], "0")
        self.assertEqual(steps[0]["state_after"], "1")
        self.assertEqual(steps[1]["status"], "failed")

    def test_ordered_permutation_and_explicit_id_key(self):
        body = '''input xs:List<{event_id:Id<Event>,day:Date,priority:Int,amount:Int}>;
          define x = ordered_fold xs from 0 by k => tuple(k.day,k.priority,k.event_id)
            identified by i => i.event_id ties "reject" with s,e { yield s*10+e.amount; };
          emit "x"=x;'''
        rows = [{"event_id":"a","day":"2026-01-01","priority":"1","amount":"1"},
                {"event_id":"b","day":"2026-01-01","priority":"2","amount":"2"}]
        self.assertEqual(self.run_source(body, {"xs":rows}).to_dict()["emissions"]["x"], "12")
        self.assertEqual(self.run_source(body, {"xs":list(reversed(rows))}).to_dict()["emissions"]["x"], "12")

    def test_ties_and_duplicate_id_fail_before_step(self):
        body = '''input xs:List<{event_id:Id<Event>,day:Date}>;
          define x = ordered_fold xs from 0 by k => k.day identified by i => i.event_id
            ties "reject" with s,e { require false else "STEP"; yield s; }; emit "x"=x;'''
        for rows, code in [
            ([{"event_id":"a","day":"2026-01-01"},{"event_id":"b","day":"2026-01-01"}], "UNRESOLVED_EVENT_ORDER"),
            ([{"event_id":"a","day":"2026-01-01"},{"event_id":"a","day":"2026-01-02"}], "DUPLICATE_EVENT_ID")]:
            out = self.run_source(body, {"xs":rows})
            self.assertEqual(out.diagnostics[0]["code"], code)
            self.assertFalse(any(t["kind"] == "fold_step" for t in out.trace))

    def test_type_preservation_and_two_distinct_binders(self):
        for expr in ['fold [1] from 0 with s,e { yield true; }',
                     'fold [1] from 0 with s,s { yield s; }']:
            with self.assertRaises(SPLException):
                check(parse(schedule('define x='+expr+';')))

    def test_record_state_appends_history(self):
        out = self.run_source('''define x:{total:Int,history:List<Int>} =
          fold [2,3] from {total:0,history:[]} with s,e {
            yield {total:s.total+e,history:append(s.history,s.total+e)};
          }; emit "x"=x;''')
        self.assertEqual(out.to_dict()["emissions"]["x"], {"total":"5","history":["2","5"]})

    def test_fixed_input_resource_envelope_fails_atomically(self):
        out = self.run_source('input xs:List<Int>; define x=fold xs from 0 with s,e { require false else "STEP"; yield s+e; }; emit "x"=x;',{"xs":["0"]*100001})
        self.assertEqual(out.diagnostics[0]["code"],"RESOURCE_LIMIT")
        self.assertEqual(out.emissions,{})

    def test_advance_issue_then_earn_is_causal(self):
        body = '''input events:List<{kind:Text,amount:Money<USD>}>;
          define result:{balance:Money<USD>,pay:Money<USD>} = fold events
            from {balance:USD 0,pay:USD 0} with s,e {
              define recovery = min(s.balance,e.amount);
              yield if e.kind == "issue" then {balance:s.balance+e.amount,pay:s.pay}
                else {balance:s.balance-recovery,pay:s.pay+e.amount-recovery};
            }; emit "result"=result;'''
        issue = {"kind":"issue","amount":{"value":"15000","currency":"USD"}}
        earn = {"kind":"earn","amount":{"value":"10000","currency":"USD"}}
        first = self.run_source(body,{"events":[issue,earn]}).to_dict()["emissions"]["result"]
        second = self.run_source(body,{"events":[earn,issue]}).to_dict()["emissions"]["result"]
        self.assertEqual(first,{"balance":"5000","pay":"0"})
        self.assertEqual(second,{"balance":"15000","pay":"10000"})


if __name__ == "__main__":
    unittest.main()

