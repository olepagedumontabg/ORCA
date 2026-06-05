namespace ORCA.Api.Services.Interface;

public interface ISearchService
{
    /// <summary>
    /// Returns autocomplete suggestions for a SKU or product name prefix.
    /// When <paramref name="exactSkus"/> is false (default), config rows are
    /// grouped under their explicit Parent ID (e.g. 420006-501-001 → 420006);
    /// products without a Parent ID surface under their own full SKU — no
    /// stripping. Suitable for the main product search.
    /// When <paramref name="exactSkus"/> is true, actual stored SKUs are
    /// returned without any grouping — required for the overrides page so
    /// that the value selected is always a real product row.
    /// </summary>
    Task<SearchSuggestResult> SuggestAsync(string query, bool exactSkus = false);
}

public record SearchSuggestResult(
    List<string> Suggestions,
    List<string> DisplaySuggestions,
    List<string> Categories
);
