# Text Display Widget

A Text Display widget in a VCF Operations dashboard can show a page of HTML. This page records what the widget keeps and drops, tested on the pack's test instance, so that dashboards and their content can be planned. It is not a feature of the pack. The pack ships no Text Display widgets.

## How to add a page

1. In VCF Operations, open **Configurations**, then **Text Widget Content**, and add a file.
2. Turn on **Free format**. Without it, the editor checks that the text is XML and rejects HTML with "The XML file is incorrect."
3. Paste the HTML, and save.
4. In the Text Display widget, set **View mode** to **HTML**, and select the file in the **File** field.

The file is stored in the VCF Operations database, not as a file on disk. To export or import it from the appliance, use `ops-cli.sh file export|import|list txtwidget`. On the test appliance, the CLI failed with `NoClassDefFoundError: org/slf4j/LoggerFactory`, because the `opscli.jar` manifest names `slf4j-api-2.0.17.jar` while `lib/` holds `slf4j-api-2.0.18.jar`.

## What the widget shows

| Content | Result |
|---|---|
| Headings, paragraphs, bold, italic, underline, strike, mark, code, sub, sup, blockquote, preformatted text, line breaks, horizontal rules | Shown |
| Lists, nested lists, definition lists, `details` and `summary` | Shown |
| Tables, including `colspan` and `rowspan` | Shown, without borders, because the table rules in the `<style>` block are not applied |
| Form controls: text input, checkbox, radio, select, button, progress, meter | Shown |
| Links, including anchors within the page | Shown |
| Inline `style="..."` attributes | Applied |
| `<style>` block | Not applied |
| Inline SVG | Shown |
| Image in a relative path, such as `test-image.png` | Broken image: no sibling files are served |
| Image as a `data:` URI | Not shown. The cause is not confirmed |
| Image from an external URL | Broken image |
| `<script>`, inline or from `src` | Not run |
| Canvas drawn by a script | Empty |

## Limits

- **One file per entry.** There is no separate CSS file or image file. Use inline `style` attributes for styling, and inline SVG for images.
- **Scripts do not run.** The widget cannot show live VCF Operations data, such as object names or metric values, from this content.
- **Live data needs another route.** Not tested. Options to test: the widget's URL mode, pointing at a page that runs its own scripts, or a Text Display file in a folder set by `textDisplay_root` in `web.properties`.

## Test page

The page used for these results covers each row of the table above, with one section per test. The page is not part of the pack.
