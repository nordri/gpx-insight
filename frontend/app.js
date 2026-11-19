"use strict";

(() => {
  const MAX_FILE_SIZE = 5 * 1024 * 1024;
  const TEXT = {
    es: {
      headerNote: "Tu próxima aventura, en una imagen",
      eyebrow: "Rutas que cuentan historias",
      title: "Tu ruta, lista para compartir.",
      description: "Convierte tus rutas GPX en infografías listas para compartir.",
      fileHeading: "Elige tu archivo GPX",
      fileDescription: "Tu ruta se procesa de forma segura y no se almacena.",
      dropTitle: "Arrastra tu GPX aquí",
      dropCopy: "o selecciónalo desde tu dispositivo",
      chooseFile: "Seleccionar archivo",
      fileLimit: "Archivo .gpx · máximo 5 MiB",
      replaceFile: "Cambiar",
      themeLabel: "Tema",
      languageLabel: "Idioma / Language",
      generate: "Generar infografía",
      processing: "Generando infografía…",
      resultHeading: "Tu infografía está lista",
      resultDescription: "Descárgala o crea otra con una ruta diferente.",
      download: "Descargar PNG",
      anotherRoute: "Generar otra",
      privacy: "Tus archivos se envían directamente a la API para generar la imagen. No se guardan en esta página.",
      invalidExtension: "Selecciona un archivo con extensión .gpx.",
      fileTooLarge: "El archivo supera el límite máximo de 5 MiB.",
      emptyFile: "El archivo está vacío. Elige un GPX que contenga una ruta.",
      invalidConfig: "La URL de la API no está configurada. Revisa frontend/config.js o inicia el servidor local con make floci-frontend.",
      connectionError: "No se pudo conectar con la API. Comprueba que esté disponible y que permita CORS para esta página.",
      timeoutError: "La solicitud tardó demasiado. Inténtalo de nuevo.",
      unexpectedResponse: "La API devolvió una respuesta inesperada. Inténtalo de nuevo más tarde.",
      serverError: "No se pudo generar la infografía. Inténtalo de nuevo.",
      httpError: "La API respondió con un error (HTTP {status}).",
      errorCodes: {
        EMPTY_BODY: "El archivo GPX está vacío.",
        INVALID_GPX: "El archivo no contiene una ruta GPX válida.",
        INVALID_PARAMETERS: "La combinación de tema o idioma no es válida.",
        PAYLOAD_TOO_LARGE: "El archivo supera el límite máximo de 5 MiB.",
        UNSUPPORTED_MEDIA_TYPE: "La API no aceptó el tipo de archivo enviado.",
        INTERNAL_ERROR: "Ocurrió un error al generar la infografía. Inténtalo más tarde."
      }
    },
    en: {
      headerNote: "Your next adventure, in one image",
      eyebrow: "Routes that tell stories",
      title: "Your route, ready to share.",
      description: "Turn your GPX routes into infographics made to share.",
      fileHeading: "Choose your GPX file",
      fileDescription: "Your route is processed securely and is not stored.",
      dropTitle: "Drop your GPX here",
      dropCopy: "or choose it from your device",
      chooseFile: "Choose file",
      fileLimit: ".gpx file · 5 MiB maximum",
      replaceFile: "Change",
      themeLabel: "Theme",
      languageLabel: "Language / Idioma",
      generate: "Generate infographic",
      processing: "Generating infographic…",
      resultHeading: "Your infographic is ready",
      resultDescription: "Download it or create another from a different route.",
      download: "Download PNG",
      anotherRoute: "Create another",
      privacy: "Your files are sent directly to the API to generate the image. They are not stored on this page.",
      invalidExtension: "Choose a file with the .gpx extension.",
      fileTooLarge: "The file exceeds the 5 MiB maximum size.",
      emptyFile: "The file is empty. Choose a GPX file that contains a route.",
      invalidConfig: "The API URL is not configured. Check frontend/config.js or start the local server with make floci-frontend.",
      connectionError: "Could not connect to the API. Check that it is available and allows CORS for this page.",
      timeoutError: "The request took too long. Please try again.",
      unexpectedResponse: "The API returned an unexpected response. Please try again later.",
      serverError: "Could not generate the infographic. Please try again.",
      httpError: "The API returned an error (HTTP {status}).",
      errorCodes: {
        EMPTY_BODY: "The GPX file is empty.",
        INVALID_GPX: "The file does not contain a valid GPX route.",
        INVALID_PARAMETERS: "The selected theme or language is not valid.",
        PAYLOAD_TOO_LARGE: "The file exceeds the 5 MiB maximum size.",
        UNSUPPORTED_MEDIA_TYPE: "The API did not accept the uploaded file type.",
        INTERNAL_ERROR: "An error occurred while generating the infographic. Please try again later."
      }
    }
  };

  const form = document.querySelector("#generate-form");
  const fileInput = document.querySelector("#gpx-file");
  const dropZone = document.querySelector("#drop-zone");
  const chooseFileButton = document.querySelector("#choose-file");
  const replaceFileButton = document.querySelector("#replace-file");
  const selectedFile = document.querySelector("#selected-file");
  const fileName = document.querySelector("#file-name");
  const fileSize = document.querySelector("#file-size");
  const themeSelect = document.querySelector("#theme");
  const languageSelect = document.querySelector("#language");
  const generateButton = document.querySelector("#generate-button");
  const statusMessage = document.querySelector("#status-message");
  const result = document.querySelector("#result");
  const resultImage = document.querySelector("#result-image");
  const downloadLink = document.querySelector("#download-link");
  const anotherRouteButton = document.querySelector("#another-route");

  let gpxFile = null;
  let isGenerating = false;
  let resultObjectUrl = null;

  function currentText(key) {
    return TEXT[languageSelect.value][key];
  }

  function setStatus(message, isError = false) {
    statusMessage.textContent = message;
    statusMessage.classList.toggle("is-error", isError);
  }

  function applyLanguage() {
    const language = languageSelect.value;
    document.documentElement.lang = language;
    document.querySelectorAll("[data-i18n]").forEach((element) => {
      const key = element.dataset.i18n;
      if (TEXT[language][key]) {
        element.textContent = TEXT[language][key];
      }
    });
    resultImage.alt = language === "es"
      ? "Infografía generada de la ruta"
      : "Generated route infographic";
    if (isGenerating) {
      generateButton.querySelector(".button-label").textContent = currentText("processing");
    }
  }

  function formatFileSize(bytes) {
    if (bytes < 1024) {
      return `${bytes} B`;
    }
    if (bytes < 1024 * 1024) {
      return `${(bytes / 1024).toFixed(1)} KiB`;
    }
    return `${(bytes / (1024 * 1024)).toFixed(2)} MiB`;
  }

  function updateSelectedFile(file) {
    gpxFile = file;
    fileName.textContent = file.name;
    fileSize.textContent = formatFileSize(file.size);
    selectedFile.hidden = false;
    generateButton.disabled = false;
  }

  function acceptFile(file) {
    if (isGenerating) {
      return;
    }
    if (!file.name.toLowerCase().endsWith(".gpx")) {
      gpxFile = null;
      selectedFile.hidden = true;
      generateButton.disabled = true;
      setStatus(currentText("invalidExtension"), true);
      return;
    }
    if (file.size > MAX_FILE_SIZE) {
      gpxFile = null;
      selectedFile.hidden = true;
      generateButton.disabled = true;
      setStatus(currentText("fileTooLarge"), true);
      return;
    }
    if (file.size === 0) {
      gpxFile = null;
      selectedFile.hidden = true;
      generateButton.disabled = true;
      setStatus(currentText("emptyFile"), true);
      return;
    }

    updateSelectedFile(file);
    setStatus("");
  }

  function resetResult() {
    if (resultObjectUrl) {
      URL.revokeObjectURL(resultObjectUrl);
      resultObjectUrl = null;
    }
    resultImage.removeAttribute("src");
    downloadLink.removeAttribute("href");
    result.hidden = true;
  }

  function apiUrl() {
    const configuredUrl = window.GPX_INSIGHT_CONFIG?.apiUrl;
    if (typeof configuredUrl !== "string" || configuredUrl.trim() === "") {
      throw new Error("api-config");
    }
    const url = new URL(configuredUrl);
    if (url.protocol !== "http:" && url.protocol !== "https:") {
      throw new Error("api-config");
    }
    url.searchParams.set("theme", themeSelect.value);
    url.searchParams.set("lang", languageSelect.value);
    return url;
  }

  async function errorMessage(response) {
    const fallback = TEXT[languageSelect.value].httpError.replace("{status}", response.status);
    const contentType = response.headers.get("content-type") || "";
    if (!contentType.toLowerCase().includes("application/json")) {
      return fallback;
    }
    try {
      const payload = await response.json();
      const knownMessage = TEXT[languageSelect.value].errorCodes[payload.code];
      return knownMessage || fallback;
    } catch (error) {
      if (error instanceof SyntaxError) {
        return fallback;
      }
      throw error;
    }
  }

  function downloadName() {
    const stem = gpxFile.name.replace(/\.gpx$/i, "")
      .normalize("NFKD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/[^a-zA-Z0-9_-]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .slice(0, 80);
    return `gpx-insight-${stem || "ruta"}.png`;
  }

  async function generateInfographic(event) {
    event.preventDefault();
    if (isGenerating || !gpxFile) {
      return;
    }

    let url;
    try {
      url = apiUrl();
    } catch (error) {
      if (error.message === "api-config" || error instanceof TypeError) {
        setStatus(currentText("invalidConfig"), true);
        return;
      }
      throw error;
    }

    isGenerating = true;
    generateButton.disabled = true;
    chooseFileButton.disabled = true;
    replaceFileButton.disabled = true;
    themeSelect.disabled = true;
    languageSelect.disabled = true;
    anotherRouteButton.disabled = true;
    generateButton.classList.add("is-loading");
    generateButton.querySelector(".button-label").textContent = currentText("processing");
    setStatus("");

    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 120_000);
    try {
      const response = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/gpx+xml" },
        body: gpxFile,
        signal: controller.signal
      });

      if (!response.ok) {
        setStatus(await errorMessage(response), true);
        return;
      }

      const contentType = response.headers.get("content-type") || "";
      if (contentType.toLowerCase().split(";", 1)[0].trim() !== "image/png") {
        setStatus(currentText("unexpectedResponse"), true);
        return;
      }

      const blob = await response.blob();
      if (blob.size === 0 || blob.type.toLowerCase() !== "image/png") {
        setStatus(currentText("unexpectedResponse"), true);
        return;
      }

      resetResult();
      resultObjectUrl = URL.createObjectURL(blob);
      resultImage.src = resultObjectUrl;
      downloadLink.href = resultObjectUrl;
      downloadLink.download = downloadName();
      result.hidden = false;
      setStatus("");
      result.scrollIntoView({ behavior: "smooth", block: "nearest" });
    } catch (error) {
      if (error.name === "AbortError") {
        setStatus(currentText("timeoutError"), true);
      } else if (error instanceof TypeError) {
        setStatus(currentText("connectionError"), true);
      } else {
        setStatus(currentText("serverError"), true);
      }
    } finally {
      window.clearTimeout(timeout);
      isGenerating = false;
      generateButton.disabled = !gpxFile;
      chooseFileButton.disabled = false;
      replaceFileButton.disabled = false;
      themeSelect.disabled = false;
      languageSelect.disabled = false;
      anotherRouteButton.disabled = false;
      generateButton.classList.remove("is-loading");
      generateButton.querySelector(".button-label").textContent = currentText("generate");
    }
  }

  function openFilePicker() {
    fileInput.click();
  }

  chooseFileButton.addEventListener("click", openFilePicker);
  replaceFileButton.addEventListener("click", openFilePicker);
  fileInput.addEventListener("change", () => {
    if (fileInput.files.length > 0) {
      acceptFile(fileInput.files[0]);
    }
    fileInput.value = "";
  });
  languageSelect.addEventListener("change", applyLanguage);
  form.addEventListener("submit", generateInfographic);

  for (const eventName of ["dragenter", "dragover"]) {
    dropZone.addEventListener(eventName, (event) => {
      event.preventDefault();
      dropZone.classList.add("is-dragging");
    });
  }
  for (const eventName of ["dragleave", "drop"]) {
    dropZone.addEventListener(eventName, (event) => {
      event.preventDefault();
      dropZone.classList.remove("is-dragging");
    });
  }
  dropZone.addEventListener("drop", (event) => {
    const [file] = event.dataTransfer.files;
    if (file) {
      acceptFile(file);
    }
  });

  anotherRouteButton.addEventListener("click", () => {
    gpxFile = null;
    fileInput.value = "";
    selectedFile.hidden = true;
    generateButton.disabled = true;
    resetResult();
    setStatus("");
    dropZone.scrollIntoView({ behavior: "smooth", block: "center" });
    openFilePicker();
  });

  applyLanguage();
})();
