---
title: "FRONTEND"
layout: default
permalink: /categories/frontend/
---

<div class="main-container">
  <div class="content-container">
    <h1 class="category-page__title">FRONTEND</h1>

    <div class="posts-grid">
      {% assign posts = site.categories["FRONTEND"] %}
      {% for post in posts %}
        {% include archive-single.html type="card" %}
      {% endfor %}
    </div>
  </div>
</div>
