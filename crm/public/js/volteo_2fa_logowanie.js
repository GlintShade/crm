// ops#422: krok kodu na stronie logowania. Rdzen Frappe dostaje `qrcode` i go nie rysuje,
// a teksty ma po angielsku. Nadpisanie po wyrenderowaniu strony (login.js definiuje funkcje wyzej).
$(document).on("login_rendered", function () {
	var rdzen = window.continue_otp_app;
	window.continue_otp_app = function (setup, qrcode) {
		if (!qrcode) {
			rdzen.apply(this, arguments);
			if (setup) {
				$("#qr_info").text("Wpisz kod z aplikacji z kodami.");
			}
			return;
		}
		window.request_otp();
		var box = $('<div class="text-muted" id="qr_info" style="padding-bottom: 15px; text-align: center;"></div>');
		box.append($("<div>").text("Zeskanuj kod aplikacją z kodami (np. Google Authenticator) i wpisz 6 cyfr."));
		box.append(
			$("<img>")
				.attr("id", "volteo_qr")
				.attr("alt", "Kod QR")
				.attr("src", "data:image/svg+xml;base64," + qrcode)
				.css({ width: "200px", height: "200px", margin: "10px auto", display: "block" })
		);
		$("#otp_div").prepend(box);
	};
});
