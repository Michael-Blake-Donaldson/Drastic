"""LeafletMapView — QWebEngineView wrapper rendering an OpenStreetMap tile map.

The widget maintains the same public surface as the old ScenarioMapCanvas so
the rest of main_window.py can stay unchanged:

    set_location(lat, lon, label)
    set_overlay_and_events(resource_overlay, event_markers)

All map mutations go through runJavaScript so the page never needs to reload.
The Leaflet JS and CSS are loaded from the official CDN; the rest of the HTML
is self-contained so the tab works offline once tiles are cached by the browser
engine.
"""
from __future__ import annotations

import json

from PySide6.QtCore import QUrl
from PySide6.QtWebEngineWidgets import QWebEngineView

# ---------------------------------------------------------------------------
# Static HTML page loaded once.  All dynamic updates are done via JS calls.
# ---------------------------------------------------------------------------

_LEAFLET_CSS = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
_LEAFLET_JS  = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"

_MAP_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>DRASTIC Operational Map</title>
  <link rel="stylesheet" href="{leaflet_css}"/>
  <style>
    html, body, #map {{ margin:0; padding:0; height:100%; width:100%; }}
    .drastic-label {{
      background: rgba(255,255,255,0.88);
      border: 1px solid #7390a2;
      border-radius: 4px;
      padding: 3px 7px;
      font: 13px/1.4 "Segoe UI Variable", "Segoe UI", sans-serif;
      color: #0f5679;
      font-weight: 600;
      white-space: nowrap;
      pointer-events: none;
    }}
    .event-dot {{
      border-radius: 50%;
      border: 2px solid rgba(255,255,255,0.85);
      display: flex;
      align-items: center;
      justify-content: center;
      font: bold 10px "Segoe UI Variable", "Segoe UI", sans-serif;
      color: #fff;
    }}
  </style>
</head>
<body>
  <div id="map"></div>
  <script src="{leaflet_js}"></script>
  <script>
    // ------------------------------------------------------------------ setup
    var map = L.map('map', {{
      zoomControl: true,
      attributionControl: true
    }}).setView([20, 0], 2);

    L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
      maxZoom: 18,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }}).addTo(map);

    // ------------------------------------------------------------------ state
    var _scenarioMarker = null;
    var _eventMarkers   = [];
    var _overlayCircle  = null;

    var _statusColors = {{
      critical: '#d94040',
      warning:  '#e6a71a',
      good:     '#2da84a',
      normal:   '#1474a3'
    }};

    var _eventConfig = {{
      resource:  {{ bg:'#e67e22', icon:'R' }},
      unmet_need:{{ bg:'#e74c3c', icon:'!' }},
      personnel: {{ bg:'#2980b9', icon:'P' }},
      transport: {{ bg:'#8e44ad', icon:'T' }},
      _default:  {{ bg:'#c0392b', icon:'?' }}
    }};

    // ----------------------------------------------------------------- helpers
    function classifyEvent(code) {{
      if (code.indexOf('resource') !== -1) return _eventConfig.resource;
      if (code === 'unmet_need')            return _eventConfig.unmet_need;
      if (code.indexOf('personnel') !== -1) return _eventConfig.personnel;
      if (code.indexOf('transport') !== -1) return _eventConfig.transport;
      return _eventConfig._default;
    }}

    function makeEventIcon(cfg) {{
      return L.divIcon({{
        html: '<div class="event-dot" style="width:20px;height:20px;background:' + cfg.bg + ';">' + cfg.icon + '</div>',
        className: '',
        iconSize: [20, 20],
        iconAnchor: [10, 10]
      }});
    }}

    function scenarioIcon(color) {{
      var svg = '<svg xmlns="http://www.w3.org/2000/svg" width="28" height="36" viewBox="0 0 28 36">'
        + '<path d="M14 0C6.27 0 0 6.27 0 14c0 10.5 14 22 14 22s14-11.5 14-22C28 6.27 21.73 0 14 0z" fill="' + color + '"/>'
        + '<circle cx="14" cy="14" r="6" fill="white"/>'
        + '</svg>';
      return L.divIcon({{
        html: svg,
        className: '',
        iconSize: [28, 36],
        iconAnchor: [14, 36],
        popupAnchor: [0, -36]
      }});
    }}

    // ------------------------------------------------------------------ API
    // Called from Python via runJavaScript.

    function setLocation(lat, lon, label) {{
      if (_scenarioMarker) {{
        map.removeLayer(_scenarioMarker);
        _scenarioMarker = null;
      }}
      if (lat === null || lon === null) {{ return; }}
      _scenarioMarker = L.marker([lat, lon], {{
        icon: scenarioIcon('#135f90'),
        title: label,
        alt: label
      }}).addTo(map)
        .bindPopup('<div class="drastic-label">' + label + '<br/>'
          + 'Lat: ' + lat.toFixed(4) + '&nbsp;&nbsp;Lon: ' + lon.toFixed(4) + '</div>');

      // Animate to location without snapping
      map.flyTo([lat, lon], 6, {{ animate: true, duration: 0.8 }});
    }}

    function setOverlayAndEvents(statusKey, events) {{
      // Overlay circle around scenario marker
      if (_overlayCircle) {{ map.removeLayer(_overlayCircle); _overlayCircle = null; }}
      if (_scenarioMarker) {{
        var lat = _scenarioMarker.getLatLng().lat;
        var lon = _scenarioMarker.getLatLng().lng;
        var color = _statusColors[statusKey] || _statusColors.normal;
        _overlayCircle = L.circle([lat, lon], {{
          radius: 120000,          // 120 km operational radius
          color: color,
          weight: 2,
          fillColor: color,
          fillOpacity: 0.12
        }}).addTo(map);
      }}

      // Clear old event markers
      _eventMarkers.forEach(function(m) {{ map.removeLayer(m); }});
      _eventMarkers = [];

      if (!events || events.length === 0) {{ return; }}

      // Spread event markers around the scenario centroid in a small circle
      var base = _scenarioMarker ? _scenarioMarker.getLatLng() : {{ lat: 20, lng: 0 }};
      var count = events.length;
      events.forEach(function(ev, i) {{
        var angle  = (2 * Math.PI * i) / count;
        var radius = 0.6;  // degrees (~67 km), purely for visual separation
        var evLat  = base.lat + radius * Math.sin(angle);
        var evLon  = base.lng + radius * Math.cos(angle);
        var cfg    = classifyEvent(ev.code);
        var m = L.marker([evLat, evLon], {{ icon: makeEventIcon(cfg), title: ev.description }})
          .addTo(map)
          .bindPopup('<b>' + ev.description + '</b><br/><small>' + ev.details + '</small>');
        _eventMarkers.push(m);
      }});
    }}
  </script>
</body>
</html>
""".format(leaflet_css=_LEAFLET_CSS, leaflet_js=_LEAFLET_JS)


class LeafletMapView(QWebEngineView):
    """Drop-in replacement for ScenarioMapCanvas backed by OpenStreetMap tiles."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(380)
        self.setAccessibleName("Operational Map")
        self.setToolTip("Real-tile map showing scenario location and simulation events")

        # Inject the page once. All updates go through runJavaScript after load.
        self._pending_location: tuple | None = None
        self._pending_overlay: tuple | None = None
        self._page_loaded = False
        self.loadFinished.connect(self._on_load_finished)
        self.setHtml(_MAP_HTML, QUrl("about:blank"))

    # ------------------------------------------------------------------
    # Public API — matches ScenarioMapCanvas exactly
    # ------------------------------------------------------------------

    def set_location(
        self,
        latitude: float | None,
        longitude: float | None,
        label: str,
    ) -> None:
        if not self._page_loaded:
            self._pending_location = (latitude, longitude, label)
            return
        lat_js = "null" if latitude is None else str(float(latitude))
        lon_js = "null" if longitude is None else str(float(longitude))
        safe_label = json.dumps(str(label))
        self.page().runJavaScript(f"setLocation({lat_js}, {lon_js}, {safe_label});")

    def set_overlay_and_events(
        self,
        resource_overlay: dict | None,
        event_markers: list | None,
    ) -> None:
        if not self._page_loaded:
            self._pending_overlay = (resource_overlay, event_markers)
            return
        status = (resource_overlay or {}).get("status", "normal")
        events_json = json.dumps(event_markers or [])
        safe_status = json.dumps(str(status))
        self.page().runJavaScript(f"setOverlayAndEvents({safe_status}, {events_json});")

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _on_load_finished(self, ok: bool) -> None:
        if not ok:
            return
        self._page_loaded = True
        if self._pending_location is not None:
            self.set_location(*self._pending_location)
            self._pending_location = None
        if self._pending_overlay is not None:
            self.set_overlay_and_events(*self._pending_overlay)
            self._pending_overlay = None
