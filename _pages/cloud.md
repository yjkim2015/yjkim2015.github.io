---
title: "CLOUD"
layout: default
permalink: /categories/cloud/
---

<div class="main-container">
  <div class="content-container">
    <h1 class="category-page__title">CLOUD</h1>

    <div class="posts-grid">
      {% assign posts = site.categories["CLOUD"] %}
      {% for post in posts %}
        {% include archive-single.html type="card" %}
      {% endfor %}
    </div>
  </div>
</div>
