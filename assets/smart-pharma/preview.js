"use strict";

const ASSETS = Object.freeze([
  {
    id: "hero-ai-pharma-engine",
    title: "AI 智能医药引擎",
    kind: "illustration",
    src: "./illustrations/hero-ai-pharma-engine.svg",
    description: "以透明医药引擎、分子数据与医疗终端构成的智能医药主视觉。",
  },
  {
    id: "drug-discovery-lab",
    title: "智能药物发现实验室",
    kind: "illustration",
    src: "./illustrations/drug-discovery-lab.svg",
    description: "融合自动化实验、分子筛选与实时数据分析的药物研发场景。",
  },
  {
    id: "digital-health-platform",
    title: "互联网医疗平台",
    kind: "illustration",
    src: "./illustrations/digital-health-platform.svg",
    description: "连接医生、患者、云端病历与智能设备的开放数字医疗平台。",
  },
  {
    id: "precision-medicine-data",
    title: "精准医疗数据",
    kind: "illustration",
    src: "./illustrations/precision-medicine-data.svg",
    description: "以基因、病例与预测模型呈现个体化诊疗的数据协同体系。",
  },
  {
    id: "ai-diagnosis",
    title: "AI 辅助诊断",
    kind: "icon",
    src: "./icons/ai-diagnosis.svg",
    description: "人工智能辅助影像与病情分析图标。",
  },
  {
    id: "capsule",
    title: "智能胶囊",
    kind: "icon",
    src: "./icons/capsule.svg",
    description: "药品、制剂与智能用药场景图标。",
  },
  {
    id: "molecule",
    title: "分子结构",
    kind: "icon",
    src: "./icons/molecule.svg",
    description: "分子建模与候选化合物研究图标。",
  },
  {
    id: "health-data",
    title: "健康数据",
    kind: "icon",
    src: "./icons/health-data.svg",
    description: "健康指标、趋势与智能分析图标。",
  },
  {
    id: "connected-care",
    title: "互联照护",
    kind: "icon",
    src: "./icons/connected-care.svg",
    description: "患者、医生与照护服务连接图标。",
  },
  {
    id: "medical-cloud",
    title: "医疗云",
    kind: "icon",
    src: "./icons/medical-cloud.svg",
    description: "云端医疗系统与数据服务图标。",
  },
  {
    id: "shield-check",
    title: "合规安全",
    kind: "icon",
    src: "./icons/shield-check.svg",
    description: "隐私保护、合规审核与数据安全图标。",
  },
  {
    id: "digital-twin",
    title: "数字孪生",
    kind: "icon",
    src: "./icons/digital-twin.svg",
    description: "人体数字孪生与虚拟模型图标。",
  },
  {
    id: "dna",
    title: "基因序列",
    kind: "icon",
    src: "./icons/dna.svg",
    description: "基因组、遗传信息与精准医疗图标。",
  },
  {
    id: "lab-engine",
    title: "实验引擎",
    kind: "icon",
    src: "./icons/lab-engine.svg",
    description: "自动化实验与研发计算引擎图标。",
  },
  {
    id: "prescription",
    title: "智能处方",
    kind: "icon",
    src: "./icons/prescription.svg",
    description: "电子处方、用药建议与药师服务图标。",
  },
  {
    id: "telemedicine",
    title: "远程医疗",
    kind: "icon",
    src: "./icons/telemedicine.svg",
    description: "在线问诊、远程会诊与数字医疗图标。",
  },
]);

const gallery = document.querySelector("#asset-gallery");
const countLabel = document.querySelector("#asset-count");
const tabs = Array.from(document.querySelectorAll(".filter-tab"));
const dialog = document.querySelector("#asset-dialog");
const dialogImage = document.querySelector("#dialog-image");
const dialogTitle = document.querySelector("#dialog-title");
const dialogType = document.querySelector("#dialog-type");
const dialogDescription = document.querySelector("#dialog-description");
const dialogFile = document.querySelector("#dialog-file");
const dialogBackground = document.querySelector("#dialog-background");
const dialogCopy = document.querySelector("#dialog-copy");
const dialogDownload = document.querySelector("#dialog-download");
const toast = document.querySelector("#toast");

const copyIcon = `
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <rect x="9" y="9" width="11" height="11" rx="2"></rect>
    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
  </svg>`;

const downloadIcon = `
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <path d="M12 3v12m0 0 5-5m-5 5-5-5M5 21h14"></path>
  </svg>`;

let currentFilter = "all";
let currentAssetId = ASSETS[0].id;
let toastTimer = 0;

function filename(asset) {
  return asset.src.split("/").pop();
}

function kindLabel(asset) {
  return asset.kind === "illustration" ? "配图" : "图标";
}

function createCard(asset, index) {
  const article = document.createElement("article");
  article.className = `asset-card asset-card--${asset.kind}`;
  article.dataset.kind = asset.kind;
  article.dataset.assetId = asset.id;

  article.innerHTML = `
    <button class="asset-media preview-trigger" type="button" data-id="${asset.id}" aria-label="放大预览：${asset.title}">
      <img
        class="asset-image"
        src="${asset.src}"
        alt="${asset.title} SVG ${kindLabel(asset)}"
        loading="${index < 4 ? "eager" : "lazy"}"
        decoding="async"
      />
    </button>
    <div class="asset-body">
      <div>
        <h3 class="asset-title">${asset.title}</h3>
        <p class="asset-filename">${filename(asset)}</p>
      </div>
      <p class="asset-type">${kindLabel(asset)}</p>
    </div>
    <div class="asset-actions">
      <button class="card-action copy-action" type="button" data-id="${asset.id}">
        ${copyIcon}
        复制 SVG
      </button>
      <a class="card-action card-action--download" href="${asset.src}" download="${filename(asset)}" data-download-id="${asset.id}">
        ${downloadIcon}
        下载
      </a>
    </div>`;

  return article;
}

function renderGallery() {
  const fragment = document.createDocumentFragment();
  ASSETS.forEach((asset, index) => fragment.append(createCard(asset, index)));
  gallery.replaceChildren(fragment);
  gallery.setAttribute("aria-busy", "false");
}

function applyFilter(filter) {
  currentFilter = filter;
  let visibleCount = 0;
  const assetKind = filter === "illustrations" ? "illustration" : filter === "icons" ? "icon" : null;

  document.querySelectorAll(".asset-card").forEach((card) => {
    const isVisible = filter === "all" || card.dataset.kind === assetKind;
    card.hidden = !isVisible;
    if (isVisible) visibleCount += 1;
  });

  tabs.forEach((tab) => {
    const isActive = tab.dataset.filter === filter;
    tab.classList.toggle("is-active", isActive);
    tab.setAttribute("aria-pressed", String(isActive));
  });

  const label = filter === "all" ? "全部" : filter === "illustrations" ? "配图" : "图标";
  countLabel.textContent = `${label} ${visibleCount} 项`;
}

function visibleAssets() {
  if (currentFilter === "all") return ASSETS;
  const assetKind = currentFilter === "illustrations" ? "illustration" : "icon";
  return ASSETS.filter((asset) => asset.kind === assetKind);
}

function findAsset(id) {
  return ASSETS.find((asset) => asset.id === id);
}

function updateDialog(asset) {
  if (!asset) return;

  currentAssetId = asset.id;
  dialogImage.src = asset.src;
  dialogImage.alt = `${asset.title} SVG ${kindLabel(asset)}`;
  dialogTitle.textContent = asset.title;
  dialogType.textContent = kindLabel(asset);
  dialogDescription.textContent = asset.description;
  dialogFile.textContent = filename(asset);
  dialogBackground.textContent = asset.kind === "illustration" ? "纯白 #FFFFFF" : "透明";
  dialogDownload.href = asset.src;
  dialogDownload.download = filename(asset);
  dialogCopy.dataset.id = asset.id;
  dialog.querySelector(".dialog-preview").classList.toggle("is-icon", asset.kind === "icon");
}

function openDialog(id) {
  const asset = findAsset(id);
  if (!asset) return;

  updateDialog(asset);
  if (typeof dialog.showModal === "function") {
    dialog.showModal();
    document.body.classList.add("dialog-open");
  } else {
    window.open(asset.src, "_blank", "noopener,noreferrer");
  }
}

function closeDialog() {
  if (!dialog.open) return;
  dialog.close();
  document.body.classList.remove("dialog-open");
}

function stepDialog(direction) {
  const assets = visibleAssets();
  const index = assets.findIndex((asset) => asset.id === currentAssetId);
  const nextIndex = (index + direction + assets.length) % assets.length;
  updateDialog(assets[nextIndex]);
}

function showToast(message, isError = false) {
  window.clearTimeout(toastTimer);
  toast.textContent = message;
  toast.classList.toggle("is-error", isError);
  toast.classList.add("is-visible");
  toastTimer = window.setTimeout(() => toast.classList.remove("is-visible"), 2600);
}

async function writeToClipboard(text) {
  if (navigator.clipboard && window.isSecureContext) {
    await navigator.clipboard.writeText(text);
    return;
  }

  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.opacity = "0";
  document.body.append(textarea);
  textarea.select();
  const copied = document.execCommand("copy");
  textarea.remove();
  if (!copied) throw new Error("Clipboard access was denied");
}

async function copySvg(id, button) {
  const asset = findAsset(id);
  if (!asset) return;

  const originalLabel = button?.innerHTML;
  if (button) {
    button.disabled = true;
    button.textContent = "复制中…";
  }

  try {
    const response = await fetch(asset.src, { cache: "no-store" });
    if (!response.ok) throw new Error(`SVG request failed with ${response.status}`);
    const source = await response.text();
    if (!/<svg[\s>]/i.test(source)) throw new Error("The requested file is not SVG");
    await writeToClipboard(source);
    showToast(`已复制「${asset.title}」的 SVG 源码`);
  } catch (error) {
    const localHint = window.location.protocol === "file:"
      ? "浏览器限制本地文件读取，请通过本地服务器打开预览页。"
      : "未能读取或复制 SVG，请检查文件是否存在。";
    showToast(localHint, true);
    console.error(error);
  } finally {
    if (button) {
      button.disabled = false;
      button.innerHTML = originalLabel;
    }
  }
}

function addMissingState(image) {
  if (image.classList.contains("is-missing")) return;
  image.classList.add("is-missing");
  const state = document.createElement("span");
  state.className = "missing-asset";
  state.innerHTML = `
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M4 5h16v14H4zM4 15l4-4 3 3 2-2 7 7M15.5 9.5h.01"></path>
    </svg>
    <span>SVG 文件待就绪</span>`;
  image.parentElement?.append(state);
}

renderGallery();
applyFilter("all");

tabs.forEach((tab, tabIndex) => {
  tab.addEventListener("click", () => applyFilter(tab.dataset.filter));
  tab.addEventListener("keydown", (event) => {
    const isPrevious = event.key === "ArrowLeft";
    const isNext = event.key === "ArrowRight";
    const isFirst = event.key === "Home";
    const isLast = event.key === "End";
    if (!isPrevious && !isNext && !isFirst && !isLast) return;
    event.preventDefault();
    const nextIndex = isFirst
      ? 0
      : isLast
        ? tabs.length - 1
        : (tabIndex + (isNext ? 1 : -1) + tabs.length) % tabs.length;
    tabs[nextIndex].focus();
    applyFilter(tabs[nextIndex].dataset.filter);
  });
});

gallery.addEventListener("click", (event) => {
  const preview = event.target.closest(".preview-trigger");
  if (preview) {
    openDialog(preview.dataset.id);
    return;
  }

  const copyButton = event.target.closest(".copy-action");
  if (copyButton) {
    copySvg(copyButton.dataset.id, copyButton);
    return;
  }

  const download = event.target.closest("[data-download-id]");
  if (download) {
    const asset = findAsset(download.dataset.downloadId);
    if (asset) showToast(`正在下载「${asset.title}」`);
  }
});

gallery.addEventListener(
  "error",
  (event) => {
    if (event.target.matches("img.asset-image")) addMissingState(event.target);
  },
  true,
);

dialog.querySelector(".dialog-close").addEventListener("click", closeDialog);
dialog.querySelector(".dialog-prev").addEventListener("click", () => stepDialog(-1));
dialog.querySelector(".dialog-next").addEventListener("click", () => stepDialog(1));
dialogCopy.addEventListener("click", () => copySvg(dialogCopy.dataset.id, dialogCopy));
dialogDownload.addEventListener("click", () => {
  const asset = findAsset(currentAssetId);
  if (asset) showToast(`正在下载「${asset.title}」`);
});

dialog.addEventListener("click", (event) => {
  if (event.target !== dialog) return;
  const bounds = dialog.getBoundingClientRect();
  const inside =
    event.clientX >= bounds.left &&
    event.clientX <= bounds.right &&
    event.clientY >= bounds.top &&
    event.clientY <= bounds.bottom;
  if (!inside) closeDialog();
});

dialog.addEventListener("close", () => document.body.classList.remove("dialog-open"));

document.addEventListener("keydown", (event) => {
  if (!dialog.open) return;
  if (event.key === "ArrowLeft") stepDialog(-1);
  if (event.key === "ArrowRight") stepDialog(1);
});
