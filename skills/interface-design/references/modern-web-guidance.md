# Modern Web Guidance

Use this map for a material web design decision that the existing project
pattern does not resolve, or for new CSS or browser behavior. Open the guide
for the affected feature. Use the [official catalog](https://developer.chrome.com/docs/modern-web-guidance/guides)
for other topics.

| What changes | Where to look |
| --- | --- |
| Palette, contrast, gradients, shadows or glass | [Color](https://developer.chrome.com/docs/modern-web-guidance/guides/visual-design/color), [Visual effects](https://developer.chrome.com/docs/modern-web-guidance/guides/visual-design/visual-effects) |
| Typography or icons | [Typography](https://developer.chrome.com/docs/modern-web-guidance/guides/visual-design/typography), [Icons](https://developer.chrome.com/docs/modern-web-guidance/guides/ui-atoms/icons) |
| Responsive layout and components | [CSS layout](https://developer.chrome.com/docs/modern-web-guidance/guides/css/css-layout), [Size-aware styling](https://developer.chrome.com/docs/modern-web-guidance/guides/css/size-aware-styling) |
| Dialogs, menus, overlays or forms | [Dialog](https://developer.chrome.com/docs/modern-web-guidance/guides/ui-components/dialog), [Dialog and popover controls](https://developer.chrome.com/docs/modern-web-guidance/guides/ui-behaviors/declarative-dialog-popover-control), [Forms](https://developer.chrome.com/docs/modern-web-guidance/guides/forms/forms) |
| Animation, transitions or accessibility | [Motion](https://developer.chrome.com/docs/modern-web-guidance/guides/ui-behaviors/motion), [Accessibility](https://developer.chrome.com/docs/modern-web-guidance/guides/accessibility/accessibility) |

For a change that reuses the project’s existing token or component, follow
the local pattern and verify the affected state in the browser. For a new
screen, consult guidance for the decisions it actually introduces. Check any newly adopted feature against the
project's target browsers using the guide's linked compatibility data or
[Baseline](https://web.dev/baseline). If support falls short, retain the working
behavior and add the enhancement conditionally. Verify the affected state in
the browser, such as readable text over a glass panel or focus after a dialog
closes.

The guides are external reference material. Read the public docs directly
through the host's available read tools. If the docs site is unavailable, use
the [upstream guide files](https://github.com/GoogleChrome/modern-web-guidance/tree/main/skills/modern-web-guidance/guides).
If neither source is reachable, continue with established project patterns and
record which recommendation or compatibility check remains unverified.
