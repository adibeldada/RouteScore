const API = "https://p51ce7sse8.execute-api.ca-central-1.amazonaws.com/prod";   // my API's base URL

// ===== REQUEST 1: GET /home =====
// When the page loads: all of Hamilton's numbers → fills <section id="system">
fetch(API + "/home")                                    // ask the API for /home
  .then(function (response) {                           // when the answer arrives
    return response.json();                             // envelope → object
  })
  .then(function (data) {                               // data = {on_time, late, early, total}
    document.getElementById("system").textContent = `On time: ${data.on_time}% | late: ${data.late}% | early: ${data.early}% | total: ${data.total}`;   // replace "Loading..."
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
  console.log(event.target.value);       // for now: just check what got picked

  fetch(API + "/stops/" + stopId)

});

