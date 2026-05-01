---
title: "JPA"
layout: default
permalink: /categories/jpa/
---

<div class="main-container">
  <div class="content-container">
    <h1 class="category-page__title">JPA</h1>

    <div class="posts-grid">
      {% assign posts = site.categories["JPA"] %}
      {% for post in posts %}
        {% include archive-single.html type="card" %}
      {% endfor %}
    </div>
  </div>
</div>
