using System.Text.Json;
using System.Text.RegularExpressions;

namespace ORCA.Api;

public class SnakeCaseNamingPolicy : JsonNamingPolicy
{
    public static readonly SnakeCaseNamingPolicy Instance = new();

    public override string ConvertName(string name) =>
        Regex.Replace(name, "(?<!^)([A-Z])", "_$1").ToLower();
}
