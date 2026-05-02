---
title: "TEST"
layout: default
permalink: /categories/test/
---

<div class="main-container">
  <div class="content-container">
    <h1 class="category-page__title">TEST</h1>

    <div class="posts-grid">
      {% assign posts = site.categories["TEST"] %}
      {% for post in posts %}
        {% include archive-single.html type="card" %}
      {% endfor %}
    </div>
  </div>
</div>
