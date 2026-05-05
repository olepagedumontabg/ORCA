using Microsoft.AspNetCore.Mvc;
using ORCA.Api.Services.Interface;

namespace ORCA.Api.Controllers;

[ApiController]
public class SearchController : ControllerBase
{
    private readonly ISearchService _search;

    public SearchController(ISearchService search)
    {
        _search = search;
    }

    /// <summary>
    /// GET /suggest?q=... — SKU / product name autocomplete.
    /// Returns displaySuggestions in camelCase to match the original API and existing JS.
    /// </summary>
    [HttpGet("/suggest")]
    public async Task<IActionResult> Suggest([FromQuery] string? q, [FromQuery] bool exact = false)
    {
        if (string.IsNullOrWhiteSpace(q) || q.Length < 2)
            return Ok(new { suggestions = Array.Empty<string>(), displaySuggestions = Array.Empty<string>(), categories = Array.Empty<string>() });

        var result = await _search.SuggestAsync(q, exactSkus: exact);

        return Ok(new
        {
            suggestions        = result.Suggestions,
            displaySuggestions = result.DisplaySuggestions,
            categories         = result.Categories
        });
    }
}
