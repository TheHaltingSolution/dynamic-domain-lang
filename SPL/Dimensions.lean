import Init.Data.Rat

/-! Finite, versioned dimensions admitted by the first exact quantity slice.
No implicit conversion or arbitrary user-defined unit is admitted. -/
namespace SPL.Dimensions

def dictionary : String := "spl.units/1"
def units : List String := ["Download", "UsageMinute"]
def admitted (unit : String) : Bool := units.contains unit

def usageFeature : String := "spl.usage-time/1"
def usageRelation : String := "spl.usage-time/1:minute-hour"

structure Admission where
  features : List String := []
  deriving Repr, BEq, Inhabited

/-- Runtime meanings are not source spelling permission. -/
structure Meanings where
  features : List String := []
  deriving Repr, BEq, Inhabited

structure UnitDefinition where
  id : String
  name : String
  family : String
  base : String
  scale : Rat
  pin : String
  deriving Repr, BEq, Inhabited

def definitions : List UnitDefinition := [
  ⟨"spl.units/1:Download", "Download", "download", "spl.units/1:Download", 1,
    "122e5bad98a89581237385c3429dd773399351d38c24c8f73517c8097512faf2"⟩,
  ⟨"spl.units/1:UsageMinute", "UsageMinute", "usage-duration", "spl.units/1:UsageMinute", 1,
    "505603f6840a5dbcd46695a56b2cfb8b56f202dc23a9997dc5a1b25e37f96ee3"⟩,
  ⟨"spl.units.usage-time/1:UsageHour", "UsageHour", "usage-duration", "spl.units/1:UsageMinute", 60,
    "4d042b99fff6488e5d945d69bb34e1b9e83152bde5297f3bd488abbb17a0b264"⟩]

def validateRelation (left : UnitDefinition) (leftCount : Rat)
    (right : UnitDefinition) (rightCount : Rat) : Except String Unit := do
  unless definitions.contains left && definitions.contains right do throw "UNIT_DEFINITION_MISMATCH"
  unless leftCount > 0 && rightCount > 0 && left.scale > 0 && right.scale > 0 &&
      left.family == right.family && left.base == right.base &&
      leftCount * left.scale == rightCount * right.scale do
    throw "CONVERSION_SCALE_MISMATCH"

structure Relation where
  id : String
  left : String
  leftCount : Rat
  right : String
  rightCount : Rat
  pin : String
  deriving Repr, BEq, Inhabited

def relations : List Relation := [
  ⟨usageRelation, "spl.units/1:UsageMinute", 60, "spl.units.usage-time/1:UsageHour", 1,
    "948980276c172c6462e8e013c2b17782c5a24023494c6a8e4db109d19d4a419e"⟩]

structure Feature where
  id : String
  units : List String
  relations : List String
  builtins : List String
  unitDictionary : String
  relationDictionary : String
  deriving Repr, BEq, Inhabited

def catalog : List Feature := [
  ⟨usageFeature, ["spl.units.usage-time/1:UsageHour"], [usageRelation], ["convert_quantity"],
    "spl.units.usage-time/1", "spl.conversions.usage-time/1"⟩]

def selected (features : List String) : List Feature := catalog.filter (fun entry => features.contains entry.id)

def admittedDefinitions (features : List String) : List UnitDefinition :=
  let ids := (selected features).flatMap (·.units)
  definitions.filter (fun entry => admitted entry.name || ids.contains entry.id)

def prepare (features : List String) : Except String Admission := do
  unless features.all (fun id => catalog.any (·.id == id)) do throw "UNSUPPORTED_FEATURE"
  unless features.eraseDups.length == features.length do throw "DUPLICATE_FEATURE"
  let entries := admittedDefinitions features
  unless (entries.map (·.name)).eraseDups.length == entries.length do throw "UNIT_OWNERSHIP_CONFLICT"
  for feature in selected features do
    unless feature.units.all (fun id => definitions.any (·.id == id)) &&
        feature.relations.all (fun id => relations.any (·.id == id)) do throw "INVALID_FEATURE_CATALOG"
  pure { features }

def admittedWith (context : Admission) (unit : String) : Bool :=
  (admittedDefinitions context.features).any (·.name == unit)

def known (context : Meanings) (unit : String) : Bool :=
  (admittedDefinitions context.features).any (·.name == unit)

def builtinNames (features : List String) : List String := (selected features).flatMap (·.builtins)

def hasBuiltin (context : Admission) (name : String) : Bool := (builtinNames context.features).contains name

def definitionPins (features : List String) : List (String × String) :=
  (admittedDefinitions features).map (fun entry => (entry.id, entry.pin))

def relationPins (features : List String) : List (String × String) :=
  let ids := (selected features).flatMap (·.relations)
  (relations.filter (fun entry => ids.contains entry.id)).map (fun entry => (entry.id, entry.pin))

def conversionFactor (context : Admission) (source target relation : String) : Except String Rat := do
  let _ ← prepare context.features
  let some entry := relations.find? (·.id == relation) | throw "UNSUPPORTED_CONVERSION"
  unless (selected context.features).any (fun entry => entry.relations.contains relation) do throw "FEATURE_REQUIRED"
  let some left := definitions.find? (·.name == source) | throw "CONVERSION_ENDPOINT_MISMATCH"
  let some right := definitions.find? (·.name == target) | throw "CONVERSION_ENDPOINT_MISMATCH"
  unless (left.id == entry.left && right.id == entry.right) ||
      (left.id == entry.right && right.id == entry.left) do throw "CONVERSION_ENDPOINT_MISMATCH"
  let some registeredLeft := definitions.find? (·.id == entry.left) | throw "UNSUPPORTED_CONVERSION"
  let some registeredRight := definitions.find? (·.id == entry.right) | throw "UNSUPPORTED_CONVERSION"
  validateRelation registeredLeft entry.leftCount registeredRight entry.rightCount
  pure (left.scale / right.scale)

end SPL.Dimensions
