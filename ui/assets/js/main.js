
function requestMetrics() {
  $.ajax({
    url: "/api/meterReads?tdate=yesterday&fdate=-6%20months",
  }).done(drawChart);
}

function drawChart(meterReads) {
  meterReads = JSON.parse(meterReads);
  console.log(meterReads);
  var data = new google.visualization.DataTable();
  data.addColumn('number', 'Date');
  data.addColumn('number', 'Reading');
  meterReads['value'].unshift(['Date', 'Reading'])
  var data = google.visualization.arrayToDataTable(meterReads.value);
  var options = {
    title: 'SmartMeter Texas Meter Reads',
    legend: { position: 'bottom' }
  };
  var chart = new google.visualization.LineChart(document.getElementById('mychart'));
  chart.draw(data, options);
}

google.charts.load('current', {'packages':['corechart']});
google.charts.setOnLoadCallback(requestMetrics);
