# Text Display Widget

A Text Display widget in a VCF Operations dashboard can show a page of HTML. This page lists what the widget renders and what it drops, as tested on the pack's test instance, to help plan dashboard content.

The pack uses Text Display widgets with the HTML stored in the widget itself: the two Read Me widgets of the vSphere Cluster Performance 2.0 dashboard, and the Explanation widgets of the report input dashboards. It ships no Text Widget Content files.

## How to add a page

1. In VCF Operations, open **Configurations** > **Text Widget Content**, and add a file.
2. Turn on **Free format**. Without it, the editor expects XML and rejects HTML with "The XML file is incorrect."
3. Paste the HTML and save.
4. In the Text Display widget, set **View mode** to **HTML**, and select the file in the **File** field.

The file is stored in the VCF Operations database, not on disk. To export or import it on the appliance, use `ops-cli.sh file export|import|list txtwidget`. On the test instance the CLI failed with `NoClassDefFoundError: org/slf4j/LoggerFactory`, because the `opscli.jar` manifest names `slf4j-api-2.0.17.jar` while `lib/` holds `slf4j-api-2.0.18.jar`. If you see the same error, use the UI.

## What the widget shows

| Content | Result |
|---|---|
| Headings, paragraphs, bold, italic, underline, strike, mark, code, sub, sup, blockquote, preformatted text, line breaks, horizontal rules | Shown |
| Lists, nested lists, definition lists, `details` and `summary` | Shown |
| Tables, including `colspan` and `rowspan` | Shown, but without borders, because the table rules in a `<style>` block are not applied |
| Form controls: text input, checkbox, radio, select, button, progress, meter | Shown |
| Links, including anchors within the page | Shown |
| Inline `style="..."` attributes | Applied |
| `<style>` block | Not applied |
| Inline SVG | Shown |
| Image with a relative path, such as `test-image.png` | Broken image: no other files are served |
| Image as a `data:` URI | Not shown. The cause is not known. |
| Image from an external URL | Broken image |
| `<script>`, inline or from `src` | Not run |
| Canvas drawn by a script | Empty |

## Limits

- **One file per entry.** There is no separate CSS or image file. Use inline `style` attributes for styling, and inline SVG for images.
- **Scripts do not run**, so the widget cannot show live VCF Operations data, such as object names or metric values, from this content.
- **Live data needs another route, not yet tested.** Options to try: the widget's URL mode, pointing at a page that runs its own scripts, or a Text Display file in a folder set by `textDisplay_root` in `web.properties`.

## Test page

The results above come from a test page with one section per row of the table. The test page is not part of the pack.
