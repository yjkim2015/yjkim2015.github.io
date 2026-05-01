---
title: "ARCHITECTURE"
layout: default
permalink: /categories/architecture/
---

<div class="main-container">
  <div class="content-container">
    <h1 class="category-page__title">ARCHITECTURE</h1>

    <div class="posts-grid">
      {% assign posts = site.categories["ARCHITECTURE"] %}
      {% for post in posts %}
        {% include archive-single.html type="card" %}
      {% endfor %}
    </div>
  </div>
</div>
