You do not have to know programming to contribute. It can be as simple as spreading the words in social media or your contacts. Folks like Brock [Peterson](https://www.linkedin.com/in/brockpetersonbdcvmw/) and [Dale](https://www.linkedin.com/in/dalehassinger/) have created blogs, podcast and video, so collaborate with them to spread the awareness. 

If you have a GitHub account, star this repository so it's easier for you to track.

Documentation is always an area that needs help. Using your GitHub account, fork this project, make the changes. You will automatically be listed as contributor once your changes are approved.

## Property Contribution
To add a setting of any object (entity) in vSphere, we need to know the full path and name in the API.  
For example, to add the vSphere Cluster HA property called ___

## Testing

Run the unit tests (`python -m pytest tests`, from `Management Pack`) and the live validation after any change to the adapter code. The test plan, and what each check means, is in [Live Validation Test Plan](tools/validate/validate.md).

## Documentation

The documentation is in `docs/`. `docs/README.md` is the overview and lists every page.

| The page is about... | Folder |
| :--- | :--- |
| a model or functional architecture: what the parts are for and how they relate, not formulas | `docs/concepts/` |
| what is needed before, and how to install, including dark sites | `docs/installation-guide/` |
| what to set after installing: policy, Adapter Instance, customization | `docs/configuration-guide/` |
| how to use the content: dashboards, views, reports | `docs/user-guide/` |
| a metric or KPI (a KPI is a metric): how it is calculated, its limitations | `docs/reference/metrics/` |
| a list to look up, such as keys or settings | `docs/reference/` |

Rules:

- Docs describe what is built. Planned work goes in a GitHub Issue, not in `docs/`. When it is built, its user-facing text goes into the right guide.
- One task or one topic per page. No step written in two places: link to it.
- File and folder names: lowercase, words joined by `-`, no spaces. Do not repeat the folder in the name: `metrics/cluster-risk.md`, not `metrics/cluster-risk-kpi.md`.
- Images go next to the pages that use them, in an `images/` subfolder of that guide. KPI formula images go in `docs/reference/metrics/formula/`.
- Links are relative, such as `../configuration-guide/policy.md`.
- Add every new page to the contents in `docs/README.md`.
- Check the links before a commit: `python tools/check-docs/check_links.py`. The unit tests run it too.
