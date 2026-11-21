const API = "https://p51ce7sse8.execute-api.ca-central-1.amazonaws.com/prod";   // my API's base URL


// ===== REQUEST 1: GET /home =====
// When the page loads: all of Hamilton's numbers → fills <section id="system">
fetch(API + "/home")                                    // ask the API for /home
  .then(function (response) {                           // when the answer arrives
    return response.json();                             // envelope → object
  })
  .then(function (data) {                               // data = {on_time, late, early, total}
    const system = document.getElementById("system");   // where the answer goes
    const on_time_prc = data.on_time;
    const late_prc = data.late;
    const early_prc = data.early;
    const total = data.total;

    system.textContent = `On time: ${on_time_prc}% | late: ${late_prc}% | early: ${early_prc}% | total: ${total.toLocaleString()}`;   // replace "Loading..."
  });

// ===== REQUEST 2: GET /leaderboard =====
// When the page loads: every main route → fills the leaderboard table AND the route dropdown
fetch(API + "/leaderboard")                             // ask the API for /leaderboard
  .then(function (response) {                           // when the answer arrives
    return response.json();                             // envelope → object
  })
  .then(function (data) {
    const list = document.getElementById("leaderboard");
    const picker = document.getElementById("route-picker");
    const dayPicker = document.getElementById("day-route-picker");
    list.innerHTML = ""
    let rank = 1;

    for (const route of data) {
      list.innerHTML += `<tr>
        <td>${rank}</td>
        <td>${route.name}</td>
        <td>${route.on_time}%</td>
        <td>${route.late}%</td>
        <td>${route.early}%</td>
        <td>${route.total.toLocaleString()}</td>
      </tr>`;
      picker.innerHTML += `<option value="${route.route_id}">${route.name}</option>`;
      dayPicker.innerHTML += `<option value="${route.route_id}">${route.name}</option>`;
      rank += 1;
    }
  } )

// Turn "08" into "8am", "17" into "5pm", "00" into "12am"
// Turn an hour into a range: "15" → "3–4pm", "11" → "11am–12pm", "23" → "11pm–12am"
function hourLabel(hour) {
  const start = parseInt(hour);                        // "15" → 15 (text → number)
  const end = (start + 1) % 24;                        // next hour; 23 → 0 (wraps to midnight)

  const startSuffix = start < 12 ? "am" : "pm";        // am or pm for each
  const endSuffix = end < 12 ? "am" : "pm";

  const startNum = start % 12 || 12;                   // 24h → 12h: 15 → 3, 0 → 12
  const endNum = end % 12 || 12;

  if (startSuffix === endSuffix) {
    return `${startNum}–${endNum}${endSuffix}`;        // same half of day: "3–4pm"
  }
  return `${startNum}${startSuffix}–${endNum}${endSuffix}`;   // crosses noon/midnight: "11am–12pm"
}

// ===== REQUEST 3: GET /routes/<id> =====
// When a route is picked from the dropdown: that route's hour-by-hour numbers → fills the hours table + draws the chart
let hourChart = null;                                // the current chart (null = none drawn yet)
let onTimeChart = null; 

document.getElementById("route-picker").addEventListener("change", function (event) {
  const routeId = event.target.value;                // picked option's value, e.g. "5828"
  const hoursTable = document.getElementById("route-hours");

  if (routeId === "") {                              // picked "Pick a route" again → clear
    hoursTable.innerHTML = "";
    if (hourChart !== null) {                        // remove the old chart too
      hourChart.destroy();
      hourChart = null;
    }
    if (onTimeChart !== null) {                        // remove the old chart too
      onTimeChart.destroy();
      onTimeChart = null;
    }
    for (const box of document.querySelectorAll(".chart-box")) box.hidden = true;   // hide the charts again
    return;
  }

  fetch(API + "/routes/" + routeId)                  // ask the API for this route
    .then(function (response) {
      return response.json();                        // envelope → object
    })
        .then(function (data) {                          // data = {route_id, name, overall, hours: [...]}
      hoursTable.innerHTML = "";                     // clear the last route's hours

      const labels = [];                             // x-axis: "6am", "7am", ...
      const lateValues = [];                         // late % per hour
      const earlyValues = [];                        // early % per hour
      const onTimeValues = [];    

      for (const hour of data.hours) {               // one row per hour
        hoursTable.innerHTML += `<tr>
          <td>${hourLabel(hour.hour)}</td>
          <td>${hour.on_time}%</td>
          <td>${hour.late}%</td>
          <td>${hour.early}%</td>
          <td>${hour.total.toLocaleString()}</td>
        </tr>`;

        if (hour.total < 100) continue;              // too few buses → % is noisy, leave it off the chart

        labels.push(hourLabel(hour.hour));
        lateValues.push(hour.late);
        earlyValues.push(hour.early);
        onTimeValues.push(hour.on_time);
      }

            if (hourChart !== null) {                      // a chart is already drawn → delete it first
        hourChart.destroy();
      }
      if (onTimeChart !== null) {                    // same for the on-time chart
        onTimeChart.destroy();
      }

      // Chart 1: late + early, stacked
      hourChart = new Chart(document.getElementById("hour-chart"), {
        type: "bar",
        data: {
          labels: labels,
          datasets: [
            { label: "Late %",  data: lateValues,  backgroundColor: "#d9534f" },   // red
            { label: "Early %", data: earlyValues, backgroundColor: "#f0ad4e" }    // amber
          ]
        },
        options: {
          plugins: {
            title: { display: true, text: `${data.name}: off schedule by hour` }
          },
          scales: {
            x: { stacked: true },
            y: { stacked: true, beginAtZero: true, title: { display: true, text: "% of arrivals" } }
          }
        }
      });

      // Chart 2: on time
      onTimeChart = new Chart(document.getElementById("on-time-chart"), {
        type: "bar",
        data: {
          labels: labels,
          datasets: [
            { label: "On time %", data: onTimeValues, backgroundColor: "#2681dd" }   // blue
          ]
        },
        options: {
          plugins: {
            title: { display: true, text: `${data.name}: on time by hour` }
          },
          scales: {
            y: { beginAtZero: true, max: 100, title: { display: true, text: "% of arrivals" } }
          }
        }
      });
      for (const box of document.querySelectorAll(".chart-box")) box.hidden = false;
    });   // closes .then
});       // closes the listener

// ===== REQUEST 4: GET /stops =====
// When the page loads: every stop's id + name → fills <datalist id="stop-list"> (search suggestions)
fetch(API + "/stops")
  .then(function (response) {
    return response.json();                             // envelope → object
  })
  .then(function (data) {                               // data = [{stop_id, name}, ...] (~2,353 stops)
    const datalist = document.getElementById("stop-list");

    for (const stop of data){
      datalist.innerHTML += `<option value="${stop.stop_id} – ${stop.name}">`;
    }

  });

  // ===== Stop picked: show its numbers =====
document.getElementById("stop-input").addEventListener("change", function (event) {
  const result = document.getElementById("stop-result");
  const stopId = event.target.value.split(" – ")[0];

  fetch(API + "/stops/" + stopId)
    .then(function (response) {
      if (!response.ok) {
        result.textContent = "Stop not found.";
        return null;
      }
      return response.json();                        // envelope → object
    })
    .then(function (data) {
      if (data === null) return;
      
      const stop_id = data.stop_id;
      const stop_name = data.name;
      const on_time_prc = data.on_time;
      const late_prc = data.late;
      const early_prc = data.early;
      const total = data.total;
        
      result.textContent = `${stop_id} – ${stop_name}: on time ${on_time_prc}% | late ${late_prc}% | early ${early_prc}% | ${total.toLocaleString()} arrivals`;
    });
});

// ===== REQUEST 6: GET /routes/<id>/days/<day> =====
// When the route OR the date changes: that route's numbers on that day → fills <section id="day-result">
function loadDay() {
  const result = document.getElementById("day-result");                    // where the answer goes
  const routeId = document.getElementById("day-route-picker").value;       // e.g. "5782"
  const date = document.getElementById("day-picker").value;                // e.g. "2026-11-18"

  if (routeId === "" || date === "") {                                      // one of them not picked yet
    result.textContent = "Pick a route and a day.";
    return;
  }

  fetch(API + "/routes/" + routeId + "/days/" + date)
    .then(function (response) {
      if (!response.ok) {                                                   // 404 = no data that day
        result.textContent = "No data for that day.";
        return null;
      }
      return response.json();                                               // envelope → object
    })
    .then(function (data) {
      if (data === null) return;                                            // already showed the error

      const route_name = data.name;
      const on_time_prc = data.on_time;
      const late_prc = data.late;
      const early_prc = data.early;
      const total = data.total;

      result.textContent = `${route_name} on ${date}: on time ${on_time_prc}% | late ${late_prc}% | early ${early_prc}% | ${total.toLocaleString()} arrivals`;
    });
}

document.getElementById("day-route-picker").addEventListener("change", loadDay);   // route changed → reload
document.getElementById("day-picker").addEventListener("change", loadDay);         // date changed → reload

