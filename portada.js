"use strict";
(() => {
  const jugar = document.getElementById("jugar");
  const ampliar = document.getElementById("ampliar");
  const area = document.getElementById("area-juego");
  const estado = document.getElementById("estado-carga");
  const directo = document.getElementById("acceso-directo");
  let configuracion;
  let marco;

  function direccionLocal(ruta) {
    if (typeof ruta !== "string" || !ruta.trim()) throw new Error("Ruta vacía");
    const direccion = new URL(ruta, document.baseURI);
    if (direccion.origin !== location.origin) throw new Error("Se requiere el mismo origen");
    return direccion.href;
  }

  async function leerConfiguracion() {
    if (configuracion) return configuracion;
    const respuesta = await fetch("config.json", { cache: "no-store" });
    if (!respuesta.ok) throw new Error("No se pudo leer la configuración");
    const datos = await respuesta.json();
    if (datos.en_pruebas !== true) throw new Error("La portada corresponde a una versión en pruebas");
    datos.juego = direccionLocal(datos.ruta_juego);
    document.getElementById("version").textContent = String(datos.version_fuente || "en pruebas");
    directo.href = datos.juego;
    if (datos.ruta_guia_pdf) {
      const guia = document.getElementById("guia-pdf");
      guia.href = direccionLocal(datos.ruta_guia_pdf);
      guia.hidden = false;
    }
    configuracion = datos;
    return datos;
  }

  jugar.addEventListener("click", async () => {
    if (marco) {
      area.scrollIntoView({ block: "start" });
      marco.focus();
      return;
    }
    jugar.disabled = true;
    estado.textContent = "Abriendo el juego…";
    try {
      const datos = await leerConfiguracion();
      marco = document.createElement("iframe");
      marco.title = "Convoy Rebelde — versión en pruebas";
      marco.id = "juego-convoy";
      marco.allow = "autoplay; fullscreen";
      marco.allowFullscreen = true;
      marco.src = datos.juego;
      marco.addEventListener("load", () => {
        estado.textContent = "La página del juego está abierta. Haz clic o toca dentro cuando aparezca el menú.";
      }, { once: true });
      marco.addEventListener("error", () => {
        estado.textContent = "No se pudo abrir el juego aquí. Puedes usar el acceso directo.";
      });
      document.getElementById("previo").hidden = true;
      area.appendChild(marco);
      area.dataset.abierto = "true";
      ampliar.disabled = typeof area.requestFullscreen !== "function";
      jugar.textContent = "Volver al juego";
      area.scrollIntoView({ block: "start" });
      marco.focus();
      estado.textContent = "El juego se está cargando. Cuando aparezca el menú, pulsa dentro para empezar.";
    } catch (_) {
      estado.textContent = "No se pudo abrir el juego. Vuelve a intentarlo o usa el acceso directo.";
    } finally {
      jugar.disabled = false;
    }
  });

  ampliar.addEventListener("click", async () => {
    if (!marco || typeof area.requestFullscreen !== "function") return;
    try {
      await area.requestFullscreen();
      marco.focus();
    } catch (_) {
      estado.textContent = "Puedes seguir jugando en el marco. Si aparece Pausa, pulsa Continuar dentro del juego.";
    }
  });

  // Sólo lee datos pequeños; el iframe y todos los archivos del juego esperan al clic.
  leerConfiguracion().catch(() => {});
})();
