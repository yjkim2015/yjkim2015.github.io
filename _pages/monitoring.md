---
title: "MONITORING"
layout: default
permalink: /categories/monitoring/
---

<div class="main-container">
  <div class="content-container">
    <h1 class="category-page__title">MONITORING</h1>

    {% assign posts = site.categories["MONITORING"] %}
    {% for post in posts %}
      {% include archive-single.html %}
    {% endfor %}
  </div>
</div>
