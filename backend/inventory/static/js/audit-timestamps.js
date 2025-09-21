/**
 * Format all audit timestamps on the page using the browser's local time
 * Assumes `data-timestamp` values are in UTC
 */
function formatAuditTimestamps() {
  document.querySelectorAll(".audit-timestamp").forEach(function (element) {
    const timestamp = element.getAttribute("data-timestamp");
    if (timestamp) {
      // Force UTC interpretation by appending 'Z' if not present
      const utcDate = new Date(timestamp);

      // Convert to local time automatically by toLocaleString
      element.textContent = utcDate.toLocaleString([], {
        dateStyle: "medium",
        timeStyle: "short",
      });
    }
  });
}

// Format all audit timestamps when the page loads
document.addEventListener("DOMContentLoaded", function () {
  formatAuditTimestamps();
});
