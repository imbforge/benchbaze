// Refresh list of orders asynchronously, after a period of inactivity
// at least 1 min

var idleTime = 0;
let currentRootUrl = window.location.pathname + window.location.search;

// Increment the idle time every min
function timerIncrement() {
  idleTime = idleTime + 1;
}

// Check if the page being viewed is the 'root' order list view
if (orderRootUrl == currentRootUrl) {
  $(document).ready(function () {
    // Increment the idle time counter every minute.
    var idleInterval = setInterval(timerIncrement, 1000);

    // On mouse movement or key press, refresh the order list
    // reset the idle timer
    $(this).mousemove(() => {
      if (idleTime > 59) {
        refreshOrderList();
      }
      idleTime = 0;
    });

    $(this).keypress(() => {
      if (idleTime > 59) {
        refreshOrderList();
      }
      idleTime = 0;
    });
  });
}

// AJAX request to update the order list in the background
function refreshOrderList() {
  let getNewDataUrl = window.location.href;
  $.ajax({
    url: getNewDataUrl,
    method: "GET",
    data: {},
    success: (data) => {
      $("#result_list").replaceWith($("#result_list", data));
    },
    error: (error) => {
      console.error(error);
    }
  });
}
