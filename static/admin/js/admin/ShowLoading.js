function ShowLoading() {
  var container = document.createElement("div");
  container.className = "tg-loader-container";

  var logoDiv = document.createElement("div");
  logoDiv.className = "loading-logo";
  logoDiv.setAttribute("aria-label", "Loading map viewer");
  logoDiv.setAttribute("role", "status");

  var img = document.createElement("img");
  img.className = "loading-logo-mark";
  img.src = "/static/authentication/logo-small.svg";
  img.alt = "";
  img.setAttribute("aria-hidden", "true");
  logoDiv.appendChild(img);

  var caption = document.createElement("p");
  caption.className = "loading-caption";
  caption.setAttribute("aria-hidden", "true");
  caption.textContent = "Please wait";

  container.appendChild(logoDiv);
  container.appendChild(caption);

  document.body.appendChild(container);
}
