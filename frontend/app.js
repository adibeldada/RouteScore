const API = "https://p51ce7sse8.execute-api.ca-central-1.amazonaws.com/prod";   // my API's base URL

fetch(API + "/home")                                    // ask the API for /home
  .then(function (response) {                           // when the answer arrives
    return response.json();                             // envelope → object
  })
  .then(function (data) {                               // data = {on_time, late, early, total}
    document.getElementById("system").textContent = `On time: ${data.on_time}% | late: ${data.late}% | early: ${data.early}% | total: ${data.total}`;   // replace "Loading..."
  });

fetch(API + "/leaderboard")                             // ask the API for /home
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

// When a route is picked from the dropdown, show its hour-by-hour numbers
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