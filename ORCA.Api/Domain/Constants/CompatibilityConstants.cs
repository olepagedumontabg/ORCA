namespace ORCA.Api.Domain.Constants;

public static class CompatibilityConstants
{
    /// <summary>
    /// Families that are exclusive: only compatible with themselves.
    /// </summary>
    public static readonly HashSet<string> ExclusiveFamilies = new(StringComparer.OrdinalIgnoreCase)
    {
        "olio", "vellamo", "interflo", "w&b"
    };

    /// <summary>
    /// Families allowed for Utile/Nextile walls when matched with shower bases.
    /// </summary>
    public static readonly HashSet<string> ShowerBaseUtileFamilies = new(StringComparer.OrdinalIgnoreCase)
    {
        "b3", "finesse", "distinct", "zone", "olympia", "icon", "roka", "stonea"
    };

    /// <summary>
    /// Families allowed for Utile/Nextile walls when matched with bathtubs.
    /// </summary>
    public static readonly HashSet<string> BathtubUtileFamilies = new(StringComparer.OrdinalIgnoreCase)
    {
        "nomad", "mackenzie", "exhibit", "new town", "rubix",
        "bosca", "cocoon", "corinthia"
    };

    /// <summary>
    /// Minimum gap required between fixture width and screen panel width (inches).
    /// </summary>
    public const decimal ScreenMinGap = 22m;

    /// <summary>
    /// Maximum allowed overhang for forward enclosure matching (base → enclosure).
    /// </summary>
    public const decimal EnclosureToleranceForward = 2.0m;

    /// <summary>
    /// Maximum allowed overhang for reverse enclosure matching (enclosure → base).
    /// </summary>
    public const decimal EnclosureToleranceReverse = 3.0m;

    /// <summary>
    /// Category names used in the system.
    /// </summary>
    public static class Categories
    {
        public const string ShowerBases = "Shower Bases";
        public const string Bathtubs = "Bathtubs";
        public const string Showers = "Showers";
        public const string TubShowers = "Tub Showers";
        public const string ShowerDoors = "Shower Doors";
        public const string TubDoors = "Tub Doors";
        public const string ShowerScreens = "Shower Screens";
        public const string TubScreens = "Tub Screens";
        public const string Enclosures = "Enclosures";
        public const string ReturnPanels = "Return Panels";
        public const string Walls = "Walls";
    }

    /// <summary>
    /// Standard category display ordering for shower base results.
    /// </summary>
    public static readonly string[] ShowerBaseCategoryOrder =
    {
        "Shower Doors", "Return Panels", "Enclosures", "Corner Enclosures", "Screens", "Walls"
    };

    /// <summary>
    /// Standard category display ordering for bathtub results.
    /// </summary>
    public static readonly string[] BathtubCategoryOrder =
    {
        "Tub Doors", "Tub Screens", "Walls"
    };
}
