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
    list.innerHTML = ""
        let rank = 1;
    for (const route of data) {
      list.innerHTML += `<tr>
        <td>${rank}</td>
        <td>Route ${route.route_id}</td>
        <td>${route.on_time}%</td>
        <td>${route.late}%</td>
        <td>${route.early}%</td>
        <td>${route.total.toLocaleString()}</td>
      </tr>`;
      rank += 1;
    }
  } )