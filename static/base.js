document.addEventListener("DOMContentLoaded", function () {
  const currentPath = window.location.pathname;
  const navLinks = document.querySelectorAll(".navbar a");

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
    .addEventListener("click", fetchTodayReport);
});

async function fetchTodayReport() {
  try {
    const response = await fetch("/api/daily_report");
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const report = await response.json();
    displayTodayReport(report);
  } catch (error) {
    console.error("Error fetching today's report:", error);
    document.getElementById(
      "todayReportSummary"
    ).innerHTML = `Error fetching today's report: ${error.message}`;
  }
}

function displayTodayReport(report) {
  const summaryElement = document.getElementById("todayReportSummary");
  const summaryHtml = marked.parse(report.summary);

  summaryElement.innerHTML = `
            <h3>Report for ${new Date(
              report.timestamp
            ).toLocaleDateString()}</h3>
            <div>${summaryHtml}</div>
            <p><strong>Report Count:</strong> ${report.report_count}</p>
        `;
}
