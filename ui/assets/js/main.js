
let MeterRender;
(function(MeterRender){

    MeterRender.drawChart = function drawChart(meterReads) {
        meterReads = JSON.parse(meterReads);
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
    };

    MeterRender.requestMetrics = function requestMetrics() {
        let fdate = encodeURI( $('#fdate').val() ), tdate = encodeURI( $('#tdate').val() );
        $.ajax({
            url: `/api/meterReads?fdate=${fdate}&tdate=${tdate}`,
        }).done(MeterRender.drawChart);
    };

    MeterRender.onLoad = function onLoad(event) {
        let fdate = $('#fdate'), tdate = $('#tdate');
        let sixmonths = new Date( Date.now() - (86400 * 1000 * 365) );
        let yday = new Date(Date.now() - 86400000);
        let dtopts = {
            changeMonth: true,
            changeYear: true,
            dateFormat: "yy-mm-dd"
        };
        fdate.datepicker(dtopts);
        tdate.datepicker(dtopts);

        fdate.val(`${sixmonths.getFullYear()}-${sixmonths.getMonth()+1}-${sixmonths.getDate()}`);
        tdate.val(`${yday.getFullYear()}-${yday.getMonth()+1}-${yday.getDate()}`);

        fdate.change(MeterRender.requestMetrics)
        tdate.change(MeterRender.requestMetrics)
    };
    google.charts.load('current', {'packages': ['corechart']});
    google.charts.setOnLoadCallback(MeterRender.requestMetrics);
    return MeterRender;
})(MeterRender = window.MeterRender || ( window.MeterRender = {}));

$(document).ready(MeterRender.onLoad);
