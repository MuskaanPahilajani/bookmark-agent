const backendInput = document.querySelector("#backend");
const result = document.querySelector("#result");
const count = document.querySelector("#count");

chrome.storage.sync.get("backendUrl", ({ backendUrl }) => {
  backendInput.value = backendUrl || "";
});

backendInput.addEventListener("change", () => {
  chrome.storage.sync.set({ backendUrl: backendInput.value.trim().replace(/\/$/, "") });
});

function flatten(nodes) {
  return nodes.flatMap((node) => {
    const current = node.url ? [{ id: node.id, title: node.title, url: node.url }] : [];
    return current.concat(node.children ? flatten(node.children) : []);
  });
}

async function bookmarks() {
  const tree = await chrome.bookmarks.getTree();
  const items = flatten(tree);
  count.textContent = `${items.length} saved`;
  return items;
}

async function request(endpoint, body) {
  const backend = backendInput.value.trim().replace(/\/$/, "");
  if (!backend) throw new Error("Set the Backend URL first.");
  result.textContent = "Working...";
  const response = await fetch(`${backend}/${endpoint}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  const responseText = await response.text();
  let payload;
  try {
    payload = JSON.parse(responseText);
  } catch {
    payload = null;
  }
  if (!response.ok) throw new Error(payload?.detail || `${response.status} ${response.statusText}: ${responseText}`);
  result.textContent = JSON.stringify(payload, null, 2);
}

async function run(action) {
  try {
    const items = await bookmarks();
    if (action === "sync") {
      const isEdge = /Edg\//.test(navigator.userAgent);
      await request("sync", isEdge ? { chrome: [], edge: items } : { chrome: items, edge: [] });
    }
    else await request(action, { bookmarks: items });
  } catch (error) {
    result.textContent = `Error: ${error.message}`;
  }
}

document.querySelector("#sync").addEventListener("click", () => run("sync"));
document.querySelector("#categorize").addEventListener("click", () => run("categorize"));
document.querySelector("#duplicates").addEventListener("click", () => run("duplicates"));
document.querySelector("#search-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    await request("search", { bookmarks: await bookmarks(), query: document.querySelector("#query").value.trim() });
  } catch (error) {
    result.textContent = `Error: ${error.message}`;
  }
});

bookmarks().catch(() => { count.textContent = ""; });
