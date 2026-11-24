"""Interruption/tamper controls for completed financial artifact consumption."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from spl_compiler import artifacts as publication

FIELDS = {'statement.json': 'statements', 'closing-state.json': 'closing_state'}
SUCCESS = {'status': 'calculated', 'statements': ['90'], 'closing_state': [{'quantity': '10'}]}
BLOCKED = {'status': 'blocked', 'statements': [], 'closing_state': [], 'diagnostics': [{'code': 'EXPECTED'}]}


class ArtifactPublicationTests(unittest.TestCase):
    def publish(self, folder, result=SUCCESS):
        run = publication.ArtifactPublication(folder)
        (run.work / 'source.spl').write_bytes(b'original source\n')
        run.finish(deepcopy(result), FIELDS)
        return run

    def test_completed_success_files_exact_and_explicit_reader_budget(self):
        with tempfile.TemporaryDirectory() as folder:
            run = self.publish(folder)
            self.assertEqual(publication.load_completed_result(folder), SUCCESS)
            self.assertEqual(json.loads((Path(folder) / 'statement.json').read_bytes()), ['90'])
            manifest = json.loads((Path(folder) / 'completion.json').read_bytes())
            self.assertEqual(len(manifest['files']), 4)
            self.assertEqual(manifest['invocation_id'], run.invocation_id)
            with self.assertRaises(publication.PublicationError):
                run.finish(SUCCESS, FIELDS)
            for limit in (1, 0, False):
                with self.assertRaises(publication.PublicationError):
                    publication.load_completed_result(folder, max_result_bytes=limit)

    def test_interrupted_rerun_never_consumes_stale_success(self):
        for interrupted in ('statement.json', 'closing-state.json', 'result.json', 'completion.json'):
            with self.subTest(file=interrupted), tempfile.TemporaryDirectory() as folder:
                previous = self.publish(folder)
                old_bytes = (previous.work / 'result.json').read_bytes()
                run = publication.ArtifactPublication(folder)
                original = publication._atomic_bytes
                def interrupt(path, payload):
                    if Path(path).parent == Path(folder) and Path(path).name == interrupted:
                        raise KeyboardInterrupt('injected before replacement')
                    return original(path, payload)
                with patch.object(publication, '_atomic_bytes', side_effect=interrupt):
                    with self.assertRaises(KeyboardInterrupt):
                        run.finish(SUCCESS, FIELDS)
                self.assertEqual((previous.work / 'result.json').read_bytes(), old_bytes)
                with self.assertRaises(publication.PublicationError):
                    publication.load_completed_result(folder)

    def test_completed_failed_rerun_preserves_prior_and_empty_finances(self):
        with tempfile.TemporaryDirectory() as folder:
            previous = self.publish(folder)
            following = self.publish(folder, BLOCKED)
            self.assertNotEqual(previous.invocation_id, following.invocation_id)
            self.assertTrue((previous.work / 'result.json').is_file())
            self.assertEqual(publication.load_completed_result(folder), BLOCKED)
            self.assertEqual(json.loads((Path(folder) / 'closing-state.json').read_bytes()), [])

    def test_missing_changed_bytes_sizes_paths_and_duplicate_entries_block(self):
        for mutation in ('missing', 'same_size', 'larger', 'path_escape', 'duplicate'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as folder:
                run = self.publish(folder)
                source = run.work / 'source.spl'
                marker = Path(folder) / 'completion.json'
                if mutation == 'missing': source.unlink()
                if mutation == 'same_size': source.write_bytes(b'changed source!\n')
                if mutation == 'larger': source.write_bytes(b'original source\nextra')
                if mutation in ('path_escape', 'duplicate'):
                    value = json.loads(marker.read_bytes())
                    if mutation == 'path_escape': value['files'][0]['path'] = '../outside.json'
                    else: value['files'].append(deepcopy(value['files'][0]))
                    marker.write_text(json.dumps(value), encoding='utf-8')
                with self.assertRaises(publication.PublicationError):
                    publication.load_completed_result(folder)

    def test_marker_replaced_during_validation_and_result_read_tamper_block(self):
        with tempfile.TemporaryDirectory() as folder:
            run = self.publish(folder)
            original = publication._file_hash
            def replace_marker(path):
                value = original(path)
                (Path(folder) / 'completion.json').write_bytes(run.running)
                return value
            with patch.object(publication, '_file_hash', side_effect=replace_marker):
                with self.assertRaises(publication.PublicationError):
                    publication.load_completed_result(folder)
        with tempfile.TemporaryDirectory() as folder:
            self.publish(folder)
            original = publication._read_bounded
            def change_result(path, maximum):
                payload = original(path, maximum)
                return payload.replace(b'90', b'99') if Path(path).name == 'result.json' else payload
            with patch.object(publication, '_read_bounded', side_effect=change_result):
                with self.assertRaises(publication.PublicationError):
                    publication.load_completed_result(folder)

    def test_publication_io_failure_is_explicit_and_cannot_retry_same_commit(self):
        with tempfile.TemporaryDirectory() as folder:
            self.publish(folder)
            run = publication.ArtifactPublication(folder)
            with patch.object(publication.os, 'replace', side_effect=OSError('injected disk failure')):
                with self.assertRaises(publication.PublicationError):
                    run.finish(SUCCESS, FIELDS)
            self.assertEqual(list(run.work.glob('*.tmp')), [])
            with self.assertRaises(publication.PublicationError):
                publication.load_completed_result(folder)
            with self.assertRaises(publication.PublicationError):
                run.finish(SUCCESS, FIELDS)

    def test_nonfinite_overflow_and_oversized_result_never_commit(self):
        for value in (float('nan'), float('inf'), float('-inf')):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as folder:
                run = publication.ArtifactPublication(folder)
                with self.assertRaises(publication.PublicationError):
                    run.finish({**SUCCESS, 'invalid': value}, FIELDS)
                with self.assertRaises(publication.PublicationError):
                    publication.load_completed_result(folder)
        with self.assertRaises(publication.PublicationError):
            publication._strict_json(b'{"x":1e9999}')
        with tempfile.TemporaryDirectory() as folder:
            run = publication.ArtifactPublication(folder)
            with patch.object(publication, 'MAX_RESULT_BYTES', 32):
                with self.assertRaises(publication.PublicationError):
                    run.finish(SUCCESS, FIELDS)
            with self.assertRaises(publication.PublicationError):
                publication.load_completed_result(folder)


if __name__ == '__main__':
    unittest.main()
