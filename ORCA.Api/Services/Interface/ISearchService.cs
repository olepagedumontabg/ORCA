namespace ORCA.Api.Services.Interface;

public interface ISearchService
{
    /// <summary>
    /// Returns autocomplete suggestions for a SKU or product name prefix.
    /// Deduplicates config SKUs (e.g. 420006-501-001 → 420006).
    /// </summary>
    Task<SearchSuggestResult> SuggestAsync(string query);
}

public record SearchSuggestResult(
    List<string> Suggestions,
    List<string> DisplaySuggestions,
    List<string> Categories
);
