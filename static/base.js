document.addEventListener("DOMContentLoaded", function () {
  const currentPath = window.location.pathname;
  const navLinks = document.querySelectorAll(".navbar a");
  const fiBtnLang = document.getElementById("fi-btn");
  const enBtnLang = document.getElementById("en-btn");
  const currentLang = document.getElementById("currentLang");

  fiBtnLang.addEventListener("click", (e) => {
    e.preventDefault();
    setLanguage("fi");
  });
  enBtnLang.addEventListener("click", (e) => {
    e.preventDefault();
    setLanguage("en");
  });

  function setLanguage(lang) {
    document.documentElement.lang = lang;
    localStorage.setItem("preferredLanguage", lang);
    document.querySelectorAll("[data-fi][data-en]").forEach((elem) => {
      elem.textContent = elem.getAttribute(`data-${lang}`);
    });

    currentLang.textContent = lang === "fi" ? "🇫🇮" : "🇬🇧";
  }

  function getPreferredLanguage() {
    return localStorage.getItem("preferredLanguage") || "fi";
  }

  setLanguage(getPreferredLanguage());
  navLinks.forEach((link) => {
    if (link.getAttribute("href") === currentPath) {
      link.classList.add("active");
    }
  });

  const todayReportLink = document.getElementById("todayReportLink");
  const todayReportContent = document.getElementById("todayReportContent");

  todayReportLink.addEventListener("click", function (e) {
    e.preventDefault();
    todayReportContent.style.display = "block";
    window.scrollTo(0, todayReportContent.offsetTop);
  });

  document
    .getElementById("fetchTodayReport")
    .addEventListener("click", () =>
      fetchTodayReport(document.documentElement.lang)
    );
});

async function fetchTodayReport(lang) {
  try {
    const response = await fetch(`/api/daily_report?lang=${lang}`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const report = await response.json();
    displayTodayReport(report, lang);
  } catch (error) {
    console.error("Error fetching today's report:", error);
    document.getElementById("todayReportSummary").innerHTML =
      lang === "fi"
        ? `Virhe haettaessa tämän päivän raporttia: ${error.message}`
        : `Error fetching today's report: ${error.message}`;
  }
}

function displayTodayReport(report, lang) {
  const summaryElement = document.getElementById("todayReportSummary");
  const summaryHtml = marked.parse(report.summary);

  summaryElement.innerHTML = `
            <h3>${
              lang === "fi" ? "Raportti päivälle" : "Report for"
            } ${new Date(report.timestamp).toLocaleDateString(
    lang === "fi" ? "fi-FI" : "en-US"
  )}</h3>
            <div>${summaryHtml}</div>
            <p><strong>${
              lang === "fi" ? "Raporttien määrä" : "Report Count"
            }:</strong> ${report.report_count}</p>
        `;
}
