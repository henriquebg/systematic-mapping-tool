# Systematic Mapping Tool

**Systematic Mapping Tool** is a Streamlit-based dashboard for exploring, filtering, deduplicating, and exporting bibliographic records used in systematic mapping studies, literature reviews, and evidence-based research workflows.

The tool was designed to support the screening and analysis of CSV files containing academic study metadata, such as title, authors, year, citations, abstract, journal, SJR quartile, DOI, and AI-generated takeaways.

## Features

- Upload and combine one or more CSV files.
- Automatic deduplication based on normalized DOI or, when DOI is unavailable, normalized title.
- Deduplication strategies:
  - keep the first record found;
  - keep the record with the highest citation count;
  - keep the most recent record.
- Light and dark visual themes.
- Search over title, abstract, and takeaway fields.
- Exact-term search option.
- Exclusion filter to remove records containing specific terms.
- Filters by:
  - source file;
  - publication year;
  - publication type;
  - study type;
  - publisher group;
  - domain;
  - recent publication flag;
  - source group;
  - citation range;
  - SJR quartile.
- Automatic citation range classification:
  - `0`
  - `1-9`
  - `10-49`
  - `50-99`
  - `100+`
  - `unknown`
- Interactive metrics:
  - number of filtered records;
  - total number of records;
  - average citations;
  - percentage of the current corpus.
- Interactive charts:
  - distribution by year;
  - distribution by citation range;
  - distribution by SJR quartile.
- Exploratory table with selectable rows.
- Detailed view for the selected study, including:
  - title;
  - journal or event;
  - source file;
  - year;
  - citation count;
  - SJR quartile;
  - study type;
  - DOI link;
  - takeaway;
  - full abstract.
- Highlighting of searched terms in the selected study details.
- Export of the filtered dataset as CSV.
- Copy-ready selected row output.

A recent version of Streamlit is recommended because the dashboard uses interactive dataframe row selection.

## Installation

Clone the repository:

```bash
git clone https://github.com/YOUR-USERNAME/systematic-mapping-tool.git
cd systematic-mapping-tool
```

Install the required packages:

```bash
pip install streamlit pandas plotly
```

## Running the application

Run the dashboard with:

```bash
streamlit run dashboard.py
```

After running the command, Streamlit will open the application in your browser. If it does not open automatically, access the local URL shown in the terminal, usually:

```txt
http://localhost:8501
```

## Expected CSV format

The tool reads CSV files using `pandas.read_csv()` with default settings. Therefore, the recommended format is:

- comma-separated values;
- UTF-8 encoding;
- header row in the first line;
- one study per row.

### Recommended columns

The tool works best when the CSV contains the following columns:

| Column | Description | Used for |
|---|---|---|
| `Title` | Study title | Search, deduplication fallback, table, selected study view |
| `Authors` | Study authors | Exploratory table |
| `Year` | Publication year | Year filter, temporal chart, selected study view |
| `Citations` | Citation count | Citation metrics, citation range, deduplication strategy |
| `Journal` | Journal, conference, or publication venue | Exploratory table, selected study view |
| `Journal SJR Quartile` | SJR quartile or venue quality indicator | Quartile filter and chart |
| `Study Type` | Type of study | Filter and selected study view |
| `Abstract` | Study abstract | Search and selected study view |
| `Takeaway` | Short summary or AI-generated takeaway | Search and selected study view |
| `DOI` | Digital Object Identifier | Deduplication, DOI link |

### Optional columns

The dashboard also uses the following optional columns when available:

| Column | Description | Used for |
|---|---|---|
| `publication_group_detailed` | Detailed publication type, such as journal, conference, symposium, workshop, or book chapter | Filter and table |
| `publisher_group` | Publisher group, such as ACM, IEEE, Elsevier, Springer, MDPI, etc. | Filter and table |
| `domain_guess` | Domain or application area inferred for the study | Filter and table |
| `recent_6y` | Flag indicating whether the study is recent | Filter and table |
| `source_group` | Group or scope of the source | Filter |
| `source` | Original source or search track | Table |


## Notes on CSV compatibility

- Column names are case-sensitive.
- The application expects the columns to use the exact names shown above.
- If a column is missing, the dashboard will usually continue working, but the related chart, filter, metric, or table column may not appear.
- `Year` and `Citations` should contain numeric values.
- Files using semicolon (`;`) as separator may need to be converted to comma-separated CSV before upload, unless the source code is adapted to use `sep=";"`.
- DOI values may appear as raw DOI strings, DOI URLs, or strings prefixed with `doi:`. The tool normalizes them internally.

## Deduplication logic

The deduplication process uses the following logic:

1. If the record has a DOI, the DOI is normalized and used as the deduplication key.
2. If the record does not have a DOI, the normalized title is used as a fallback key.
3. If automatic deduplication is enabled, duplicated records are removed according to the selected strategy.

Available strategies:

- **Keep first record found**: keeps the first occurrence in the combined dataset.
- **Keep highest citation count**: sorts records by citation count and keeps the most cited occurrence.
- **Keep most recent article**: sorts records by year and keeps the newest occurrence.

## Search behavior

The search field looks for terms in the following columns, when available:

- `Title`
- `Abstract`
- `Takeaway`

By default, when multiple words are typed, each word is searched separately and all words must be found somewhere in the combined text fields.

When **exact-term search** is enabled, the full search expression is treated as a single expression.

The exclusion field removes records containing the specified terms from the current results.

## Exporting results

After applying filters, the current filtered dataset can be exported using the **Download filtered data (CSV)** button. The exported file does not include internal deduplication columns.

## Citation

If this tool is used in academic work, cite the repository or the related publication when available.

Suggested citation placeholder:

```bibtex
@software{systematic_mapping_tool,
  title = {Systematic Mapping Tool},
  author = {Henrique Buzeto Galati},
  year = {2026},
  url = {https://github.com/henriquebg/systematic-mapping-tool}
}
```
