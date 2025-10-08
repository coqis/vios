function cleanupClipboardText(targetSelector) {
  const targetElement = document.querySelector(targetSelector);

  // exclude "Generic Prompt" and "Generic Output" spans from copy
  const excludedClasses = ["gp", "go"];

  const clipboardText = Array.from(targetElement.childNodes)
    .filter(
      (node) =>
        !excludedClasses.some((className) =>
          node?.classList?.contains(className)
        )
    )
    .map((node) => node.textContent)
    .filter((s) => s != "");
  return clipboardText.join("").trim();
}

// Sets copy text to attributes lazily using an Intersection Observer.
function setCopyText() {
  // The `data-clipboard-text` attribute allows for customized content in the copy
  // See: https://www.npmjs.com/package/clipboard#copy-text-from-attribute
  const attr = "clipboardText";
  // all "copy" buttons whose target selector is a <code> element
  const elements = document.querySelectorAll(
    'button[data-clipboard-target$="code"]'
  );
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      // target in the viewport that have not been patched
      if (
        entry.intersectionRatio > 0 &&
        entry.target.dataset[attr] === undefined
      ) {
        entry.target.dataset[attr] = cleanupClipboardText(
          entry.target.dataset.clipboardTarget
        );
      }
    });
  });

  elements.forEach((elt) => {
    observer.observe(elt);
  });
}

// Using the document$ observable is particularly important if you are using instant loading since
// it will not result in a page refresh in the browser
// See `How to integrate with third-party JavaScript libraries` guideline:
// https://squidfunk.github.io/mkdocs-material/customization/?h=javascript#additional-javascript




// See https://github.com/danielfrg/mkdocs-jupyter/issues/99#issuecomment-2455307893
// See https://github.com/danielfrg/mkdocs-jupyter/issues/220
// Using the document$ observable from mkdocs-material to get notified of page "reload" also if using `navigation.instant` (SSA)
document$.subscribe(function() {
    // First check if the page contains a notebook-related class
    if (document.querySelector('.jp-Notebook')) {
      // "div.md-sidebar.md-sidebar--primary" is the navigation
      // "div.md-sidebar.md-sidebar--secondary is the table of contents
      document.querySelector("div.md-sidebar.md-sidebar--primary").remove();
    //   document.querySelector("div.md-sidebar.md-sidebar--secondary").remove();
    };
    setCopyText();
  });