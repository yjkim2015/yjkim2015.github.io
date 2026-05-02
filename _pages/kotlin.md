---
title: "KOTLIN"
layout: default
permalink: /categories/kotlin/
---

<div class="main-container">
  <div class="content-container">
    <h1 class="category-page__title">KOTLIN</h1>

    <div class="posts-grid">
      {% assign posts = site.categories["KOTLIN"] %}
      {% for post in posts %}
        {% include archive-single.html type="card" %}
      {% endfor %}
    </div>
  </div>
</div>
