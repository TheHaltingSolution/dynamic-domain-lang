/-! Finite, versioned dimensions admitted by the first exact quantity slice.
No implicit conversion or arbitrary user-defined unit is admitted. -/
namespace SPL.Dimensions

def dictionary : String := "spl.units/1"
def units : List String := ["Download", "UsageMinute"]
def admitted (unit : String) : Bool := units.contains unit

end SPL.Dimensions
