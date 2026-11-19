# Third-party notices

ReelTime is © Nicholas Hadler and contributors, licensed under the
[GNU Affero General Public License v3.0 or later](LICENSE).

The following third-party files are included unmodified under their own
licences. Licence texts are included alongside the files.

| What | Where | Licence |
|---|---|---|
| [htmx](https://htmx.org) 2.0.11 | `cues/static/cues/vendor/htmx.min.js` | 0BSD (`htmx.LICENSE`) |
| [AG Grid Community](https://www.ag-grid.com) 36.3.0 | `cues/static/cues/vendor/ag-grid-community.min.js` | MIT (`ag-grid-community.LICENSE`) |
| [IBM Plex Sans](https://github.com/IBM/plex) | `cues/static/cues/vendor/ibm-plex-sans-*.woff2` | SIL OFL 1.1 (`ibm-plex-sans.LICENSE`) |
| [IBM Plex Mono](https://github.com/IBM/plex) | `cues/static/cues/vendor/ibm-plex-mono-*.woff2` | SIL OFL 1.1 (`ibm-plex-mono.LICENSE`) |
| RapidCue cue sheet template (2016 v3) | `cues/exporters/cue_sheet/rapidcue_template.xlsx` | ASCAP and BMI's published template, included unchanged so exports match what RapidCue accepts |
| Pro Tools test exports from [ptulsconv](https://github.com/iluvcapra/ptulsconv) | `fixtures/third_party/ptulsconv/` (tests only) | MIT (`LICENSE` there) |

`cues/static/cues/vendor/VERSIONS` records each vendored file's package,
version, licence and SHA-256; `scripts/vendor_assets.py` regenerates it.
Python and npm dependencies are installed from their registries, not
vendored; `uv.lock` and `package-lock.json` pin them.
