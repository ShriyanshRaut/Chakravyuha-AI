/* graph.js — criminal-network graph.
   Reads data/graph.json and data/analysis.json. No backend, no build step. */
(function () {
  "use strict";

  /* ---------- configuration you may want to tweak ---------- */

  // Types shown on first paint. Everything else is opt-in via the filters,
  // because rendering all 13 types at once produces an unreadable hairball.
  var DEFAULT_TYPES = ["PERSON", "ORGANIZATION"];

  // Relationship types drawn dashed and faint: weak co-occurrence, not a
  // stated relationship.
  var WEAK_RELATIONS = { MENTIONED_WITH: true };

  var TYPE_COLOUR = {
    PERSON: "#07294e",
    ORGANIZATION: "#e68c32",
    LOCATION: "#66b7c3",
    PHONE: "#7a9e5b",
    VEHICLE: "#9b6bbf",
    BANK_ACCOUNT: "#b8543f",
    IFSC: "#b8543f",
    DATE: "#8a97a8",
    MONEY: "#c9a227",
    EMAIL: "#5f7183",
    IMEI: "#5f7183",
    SOCIAL_HANDLE: "#5f7183",
    WEAPON: "#5f7183"
  };
  function colourFor(type) { return TYPE_COLOUR[type] || "#5f7183"; }

  /* ---------- state ---------- */

  var raw = { nodes: [], edges: [] };
  var analysis = null;
  var activeTypes = {};
  var minConfidence = 0.4;
  var searchTerm = "";
  var selectedId = null;
  var simulation = null;
  var svg, viewport, linkLayer, nodeLayer, zoomBehaviour;

  var el = {
    stage: document.getElementById("graph-stage"),
    canvas: document.getElementById("graph-canvas"),
    message: document.getElementById("stage-message"),
    status: document.getElementById("graph-status"),
    typeFilters: document.getElementById("type-filters"),
    relFilters: document.getElementById("rel-filters"),
    confSlider: document.getElementById("conf-slider"),
    confValue: document.getElementById("conf-value"),
    search: document.getElementById("node-search"),
    inspector: document.getElementById("inspector-body"),
    stats: document.getElementById("stat-strip"),
    legendMarkers: document.getElementById("legend-markers"),
    btnReset: document.getElementById("btn-reset"),
    btnAll: document.getElementById("btn-show-all"),
    btnCore: document.getElementById("btn-show-core")
  };

  var hiddenRelations = {};

  /* ---------- load ---------- */

  Promise.all([
    fetch("data/graph.json").then(check),
    fetch("data/analysis.json").then(check)
  ]).then(function (results) {
    raw = results[0];
    analysis = results[1];
    el.message.style.display = "none";
    boot();
  }).catch(function (err) {
    el.message.className = "stage-message is-error";
    el.message.textContent =
      "Could not load the network data (" + err.message + "). " +
      "Serve this folder over HTTP — browsers block fetch() on file:// URLs. " +
      "Try: python -m http.server 8000";
  });

  function check(response) {
    if (!response.ok) throw new Error(response.status + " " + response.statusText);
    return response.json();
  }

  /* ---------- boot ---------- */

  function boot() {
    DEFAULT_TYPES.forEach(function (t) { activeTypes[t] = true; });
    renderStats();
    buildTypeFilters();
    buildRelationFilters();
    renderLegendMarkers();
    setupCanvas();
    bindControls();
    draw();
  }

  function renderStats() {
    var kp = analysis.kingpin || {};
    var mm = analysis.middleman || {};
    var cards = [
      [raw.nodes.length, "Entities"],
      [raw.edges.length, "Relationships"],
      [analysis.community_count, "Clusters"],
      [kp.label || "—", "Principal influencer"],
      [mm.label || "—", "Bridging intermediary"]
    ];
    el.stats.innerHTML = cards.map(function (c) {
      return '<div class="stat-card"><span class="stat-value">' + escapeHtml(String(c[0])) +
        '</span><span class="stat-label">' + c[1] + "</span></div>";
    }).join("");
  }

  function buildTypeFilters() {
    var counts = {};
    raw.nodes.forEach(function (n) { counts[n.type] = (counts[n.type] || 0) + 1; });
    var types = Object.keys(counts).sort(function (a, b) { return counts[b] - counts[a]; });

    el.typeFilters.innerHTML = types.map(function (t) {
      return '<label class="check-row">' +
        '<input type="checkbox" data-type="' + t + '"' + (activeTypes[t] ? " checked" : "") + ">" +
        '<span class="swatch" style="background:' + colourFor(t) + '"></span>' +
        "<span>" + t.replace(/_/g, " ") + "</span>" +
        '<span class="count">' + counts[t] + "</span></label>";
    }).join("");

    el.typeFilters.addEventListener("change", function (e) {
      var t = e.target.getAttribute("data-type");
      if (!t) return;
      if (e.target.checked) activeTypes[t] = true; else delete activeTypes[t];
      draw();
    });
  }

  function buildRelationFilters() {
    var counts = {};
    raw.edges.forEach(function (l) { counts[l.type] = (counts[l.type] || 0) + 1; });
    var rels = Object.keys(counts).sort(function (a, b) { return counts[b] - counts[a]; });

    el.relFilters.innerHTML = rels.map(function (r) {
      return '<label class="check-row">' +
        '<input type="checkbox" data-rel="' + r + '" checked>' +
        "<span>" + r.replace(/_/g, " ") + "</span>" +
        '<span class="count">' + counts[r] + "</span></label>";
    }).join("");

    el.relFilters.addEventListener("change", function (e) {
      var r = e.target.getAttribute("data-rel");
      if (!r) return;
      if (e.target.checked) delete hiddenRelations[r]; else hiddenRelations[r] = true;
      draw();
    });
  }

  function renderLegendMarkers() {
    var kp = analysis.kingpin || {};
    var mm = analysis.middleman || {};
    el.legendMarkers.innerHTML =
      '<li><span class="legend-dot ring-kingpin"></span>' +
      "<span><b>" + escapeHtml(kp.label || "—") + "</b> — principal influencer " +
      "(PageRank " + (kp.pagerank != null ? kp.pagerank : "—") + ")</span></li>" +
      '<li><span class="legend-dot ring-middleman"></span>' +
      "<span><b>" + escapeHtml(mm.label || "—") + "</b> — bridging intermediary " +
      "(betweenness " + (mm.betweenness != null ? mm.betweenness : "—") + ")</span></li>";
  }

  /* ---------- canvas ---------- */

  function setupCanvas() {
    svg = d3.select("#graph-canvas");
    viewport = svg.append("g").attr("class", "viewport");
    linkLayer = viewport.append("g").attr("class", "links");
    nodeLayer = viewport.append("g").attr("class", "nodes");

    zoomBehaviour = d3.zoom()
      .scaleExtent([0.25, 4])
      .on("zoom", function (event) { viewport.attr("transform", event.transform); });
    svg.call(zoomBehaviour);

    // Clicking empty canvas clears the selection.
    svg.on("click", function (event) {
      if (event.target.tagName === "svg") { selectedId = null; renderInspector(null); draw(); }
    });
  }

  function bindControls() {
    el.confSlider.addEventListener("input", function () {
      minConfidence = Number(el.confSlider.value) / 100;
      el.confValue.textContent = "Hiding relationships below " + minConfidence.toFixed(2) + " confidence";
      draw();
    });
    el.search.addEventListener("input", function () {
      searchTerm = el.search.value.trim().toLowerCase();
      draw();
    });
    el.btnReset.addEventListener("click", function () {
      svg.transition().duration(400).call(zoomBehaviour.transform, d3.zoomIdentity);
    });
    el.btnAll.addEventListener("click", function () {
      raw.nodes.forEach(function (n) { activeTypes[n.type] = true; });
      syncTypeCheckboxes();
      draw();
    });
    el.btnCore.addEventListener("click", function () {
      activeTypes = {};
      DEFAULT_TYPES.forEach(function (t) { activeTypes[t] = true; });
      syncTypeCheckboxes();
      draw();
    });
  }

  function syncTypeCheckboxes() {
    Array.prototype.forEach.call(
      el.typeFilters.querySelectorAll("input[data-type]"),
      function (box) { box.checked = !!activeTypes[box.getAttribute("data-type")]; }
    );
  }

  /* ---------- draw ---------- */

  function visibleData() {
    var nodes = raw.nodes.filter(function (n) { return activeTypes[n.type]; });
    var index = {};
    nodes.forEach(function (n) { index[n.id] = true; });

    var links = raw.edges.filter(function (l) {
      return index[l.source] && index[l.target] &&
        l.confidence >= minConfidence && !hiddenRelations[l.type];
    });

    // d3.forceSimulation mutates the objects it is given, so hand it copies.
    // Without this, re-filtering after a drag throws on stale source/target refs.
    return {
      nodes: nodes.map(function (n) { return Object.assign({}, n); }),
      links: links.map(function (l) { return Object.assign({}, l); })
    };
  }

  function draw() {
    var data = visibleData();
    var kingpinId = analysis.kingpin ? analysis.kingpin.id : null;
    var middlemanId = analysis.middleman ? analysis.middleman.id : null;

    var degree = {};
    data.links.forEach(function (l) {
      degree[l.source] = (degree[l.source] || 0) + 1;
      degree[l.target] = (degree[l.target] || 0) + 1;
    });

    el.status.textContent =
      data.nodes.length + " entities · " + data.links.length + " relationships shown";

    var width = el.canvas.clientWidth || 900;
    var height = el.canvas.clientHeight || 700;

    if (simulation) simulation.stop();

    var link = linkLayer.selectAll("line").data(data.links, linkKey);
    link.exit().remove();
    link = link.enter().append("line").merge(link)
      .attr("class", function (d) { return "link" + (WEAK_RELATIONS[d.type] ? " weak" : ""); })
      .attr("stroke-width", function (d) { return 0.8 + d.confidence * 3.2; })
      .style("cursor", "pointer")
      .on("click", function (event, d) {
        event.stopPropagation();
        selectedId = null;
        renderEdgeInspector(d);
        highlight(null);
      });

    var node = nodeLayer.selectAll("g.node").data(data.nodes, function (d) { return d.id; });
    node.exit().remove();

    var enter = node.enter().append("g").attr("class", "node");
    enter.append("circle");
    enter.append("text").attr("dy", -14).attr("text-anchor", "middle");

    node = enter.merge(node)
      .attr("class", function (d) {
        var cls = "node";
        if (d.id === kingpinId) cls += " is-kingpin";
        if (d.id === middlemanId) cls += " is-middleman";
        if (searchTerm && d.label.toLowerCase().indexOf(searchTerm) !== -1) cls += " is-search";
        return cls;
      })
      .on("click", function (event, d) {
        event.stopPropagation();
        selectedId = d.id;
        renderInspector(d, data.links);
        highlight(d.id);
      })
      .call(d3.drag()
        .on("start", function (event, d) {
          if (!event.active) simulation.alphaTarget(0.25).restart();
          d.fx = d.x; d.fy = d.y;
        })
        .on("drag", function (event, d) { d.fx = event.x; d.fy = event.y; })
        .on("end", function (event, d) {
          if (!event.active) simulation.alphaTarget(0);
          d.fx = null; d.fy = null;
        }));

    node.select("circle")
      .attr("r", function (d) { return radiusFor(d, degree); })
      .attr("fill", function (d) { return colourFor(d.type); });

    node.select("text").text(function (d) {
      // Label the entities worth labelling; the rest would just be clutter.
      var important = d.type === "PERSON" || d.type === "ORGANIZATION" ||
        (degree[d.id] || 0) >= 3 || d.id === kingpinId || d.id === middlemanId;
      return important ? d.label : "";
    });

    simulation = d3.forceSimulation(data.nodes)
      .force("link", d3.forceLink(data.links)
        .id(function (d) { return d.id; })
        .distance(function (d) { return 150 - d.confidence * 55; })
        .strength(function (d) { return 0.25 + d.confidence * 0.5; }))
      .force("charge", d3.forceManyBody().strength(-460))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collide", d3.forceCollide().radius(function (d) {
        return radiusFor(d, degree) + 14;
      }))
      .on("tick", function () {
        link
          .attr("x1", function (d) { return d.source.x; })
          .attr("y1", function (d) { return d.source.y; })
          .attr("x2", function (d) { return d.target.x; })
          .attr("y2", function (d) { return d.target.y; });
        node.attr("transform", function (d) { return "translate(" + d.x + "," + d.y + ")"; });
      });

    if (selectedId) highlight(selectedId);
  }

  function radiusFor(d, degree) {
    var base = 6 + Math.sqrt(d.mention_count || 1) * 3.2;
    return Math.min(26, base + Math.min(8, (degree[d.id] || 0) * 0.7));
  }

  function linkKey(d) {
    var s = typeof d.source === "object" ? d.source.id : d.source;
    var t = typeof d.target === "object" ? d.target.id : d.target;
    return s + "|" + t + "|" + d.type;
  }

  /* ---------- highlighting ---------- */

  function highlight(id) {
    if (!id) {
      nodeLayer.selectAll("g.node").classed("dimmed", false);
      linkLayer.selectAll("line").classed("dimmed", false).classed("is-hit", false);
      return;
    }
    var neighbours = {};
    neighbours[id] = true;
    linkLayer.selectAll("line").each(function (d) {
      if (d.source.id === id) neighbours[d.target.id] = true;
      if (d.target.id === id) neighbours[d.source.id] = true;
    });
    nodeLayer.selectAll("g.node").classed("dimmed", function (d) { return !neighbours[d.id]; });
    linkLayer.selectAll("line")
      .classed("is-hit", function (d) { return d.source.id === id || d.target.id === id; })
      .classed("dimmed", function (d) { return d.source.id !== id && d.target.id !== id; });
  }

  /* ---------- inspector ---------- */

  function renderInspector(d, links) {
    if (!d) {
      el.inspector.innerHTML =
        '<p class="placeholder">Click any entity to see who it is connected to, ' +
        "or click a relationship line to read the sentence in the source document " +
        "that produced it.</p>";
      return;
    }

    var connections = [];
    (links || []).forEach(function (l) {
      if (l.source.id === d.id) connections.push({ rel: l.type, other: l.target, edge: l });
      else if (l.target.id === d.id) connections.push({ rel: l.type, other: l.source, edge: l });
    });
    connections.sort(function (a, b) { return b.edge.confidence - a.edge.confidence; });

    var html = '<span class="pill" style="background:' + colourFor(d.type) + '">' +
      d.type.replace(/_/g, " ") + "</span>" +
      '<h3 class="entity-title">' + escapeHtml(d.label) + "</h3>";

    if (analysis.kingpin && analysis.kingpin.id === d.id) {
      html += '<p class="kv"><b>Principal influencer</b> — highest PageRank in the network.</p>';
    }
    if (analysis.middleman && analysis.middleman.id === d.id) {
      html += '<p class="kv"><b>Bridging intermediary</b> — highest betweenness; removing ' +
        "this entity disconnects the network.</p>";
    }

    html += "<h4>Extraction confidence</h4>" +
      '<div class="meter"><span style="width:' + Math.round(d.confidence * 100) + '%"></span></div>' +
      '<p class="kv">' + d.confidence.toFixed(2) + " · mentioned " + d.mention_count +
      (d.mention_count === 1 ? " time" : " times") + "</p>";

    if (d.aliases && d.aliases.length) {
      html += "<h4>Also recorded as</h4><div class=\"chip-row\">" +
        d.aliases.map(function (a) { return '<span class="chip">' + escapeHtml(a) + "</span>"; }).join("") +
        "</div>";
    }

    html += "<h4>Appears in " + d.documents.length +
      (d.documents.length === 1 ? " source" : " sources") + "</h4><div class=\"chip-row\">" +
      d.documents.map(function (doc) {
        return '<span class="chip">' + escapeHtml(doc.replace(/_/g, " ")) + "</span>";
      }).join("") + "</div>";

    html += "<h4>" + connections.length +
      (connections.length === 1 ? " connection" : " connections") + "</h4>";

    if (connections.length) {
      html += '<ul class="conn-list">' + connections.map(function (c, i) {
        return '<li data-conn="' + i + '"><span class="rel">' + c.rel.replace(/_/g, " ") +
          "</span><br>" + escapeHtml(c.other.label) +
          ' <span class="rel">· ' + c.edge.confidence.toFixed(2) + "</span></li>";
      }).join("") + "</ul>";
    } else {
      html += '<p class="kv">No visible connections at the current filters. ' +
        "Try lowering the confidence threshold or enabling more entity types.</p>";
    }

    el.inspector.innerHTML = html;

    // Clicking a connection shows the evidence sentence behind it.
    Array.prototype.forEach.call(el.inspector.querySelectorAll("[data-conn]"), function (li) {
      li.addEventListener("click", function () {
        renderEdgeInspector(connections[Number(li.getAttribute("data-conn"))].edge);
      });
    });
  }

  function renderEdgeInspector(edge) {
    var sourceLabel = typeof edge.source === "object" ? edge.source.label : edge.source;
    var targetLabel = typeof edge.target === "object" ? edge.target.label : edge.target;

    var html = '<span class="pill light">Relationship</span>' +
      '<h3 class="entity-title">' + escapeHtml(sourceLabel) + " → " + escapeHtml(targetLabel) + "</h3>" +
      '<p class="kv"><b>' + edge.type.replace(/_/g, " ") + "</b></p>" +
      "<h4>Confidence</h4>" +
      '<div class="meter"><span style="width:' + Math.round(edge.confidence * 100) + '%"></span></div>' +
      '<p class="kv">' + edge.confidence.toFixed(2) + " · observed in " + edge.occurrences +
      (edge.occurrences === 1 ? " document" : " documents") + "</p>";

    var attrs = edge.attributes || {};
    var attrKeys = Object.keys(attrs);
    if (attrKeys.length) {
      html += "<h4>Details</h4><p class=\"kv\">" + attrKeys.map(function (k) {
        var v = attrs[k];
        if (k === "amount") v = "Rs. " + Number(v).toLocaleString("en-IN");
        return "<b>" + k + ":</b> " + escapeHtml(String(v));
      }).join("<br>") + "</p>";
    }

    // The point of the whole page: every edge traces to a sentence someone wrote.
    html += "<h4>Evidence from source documents</h4>";
    (edge.evidence || []).forEach(function (ev) {
      html += '<div class="evidence-block"><span class="doc-id">' +
        escapeHtml(ev.doc_id.replace(/_/g, " ")) + "</span><p>" +
        escapeHtml(ev.sentence) + "</p></div>";
    });
    if (!edge.evidence || !edge.evidence.length) {
      html += '<p class="kv">No sentence recorded for this relationship.</p>';
    }

    el.inspector.innerHTML = html;
  }

  function escapeHtml(str) {
    return String(str).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  window.addEventListener("resize", function () {
    if (simulation) {
      simulation.force("center",
        d3.forceCenter(el.canvas.clientWidth / 2, el.canvas.clientHeight / 2));
      simulation.alpha(0.25).restart();
    }
  });
})();
