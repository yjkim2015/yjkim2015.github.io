---
title: "BATCH"
layout: default
permalink: /categories/batch/
---

<div class="main-container">
  <div class="content-container">
    <h1 class="category-page__title">BATCH</h1>

    <div class="posts-grid">
      {% assign posts = site.categories["BATCH"] %}
      {% for post in posts %}
        {% include archive-single.html type="card" %}
      {% endfor %}
    </div>
  </div>
</div>
