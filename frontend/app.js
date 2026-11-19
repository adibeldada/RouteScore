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
function hourLabel(hour) {
  const h = parseInt(hour);                          // "08" → 8 (text → number)
  const suffix = h < 12 ? "am" : "pm";              // before noon = am
  return `${h % 12 || 12}${suffix}`;                // 17 → 5, 0 → 12
}

// ===== REQUEST 3: GET /routes/<id> =====
// When a route is picked from the dropdown: that route's hour-by-hour numbers → fills the hours table
document.getElementById("route-picker").addEventListener("change", function (event) {
  const routeId = event.target.value;                // picked option's value, e.g. "5828"
  const hoursTable = document.getElementById("route-hours");

  if (routeId === "") {                              // picked "Pick a route" again → clear
    hoursTable.innerHTML = "";
    return;
  }

  fetch(API + "/routes/" + routeId)                  // ask the API for this route
    .then(function (response) {
      return response.json();                        // envelope → object
    })
    .then(function (data) {                          // data = {route_id, name, overall, hours: [...]}
      hoursTable.innerHTML = "";                     // clear the last route's hours

      for (const hour of data.hours) {               // one row per hour
        hoursTable.innerHTML += `<tr>
          <td>${hourLabel(hour.hour)}</td>
          <td>${hour.on_time}%</td>
          <td>${hour.late}%</td>
          <td>${hour.early}%</td>
          <td>${hour.total.toLocaleString()}</td>
        </tr>`;
      }
    });
});

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

