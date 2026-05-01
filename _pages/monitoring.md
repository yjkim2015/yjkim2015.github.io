---
title: "MONITORING"
layout: default
permalink: /categories/monitoring/
---

<div class="main-container">
  <div class="content-container">
    <h1 class="category-page__title">MONITORING</h1>

    <div class="posts-grid">
      {% assign posts = site.categories["MONITORING"] %}
      {% for post in posts %}
        {% include archive-single.html type="card" %}
      {% endfor %}
    </div>
  </div>
</div>
