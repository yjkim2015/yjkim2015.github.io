---
title: "JAVA"
layout: default
permalink: /categories/java/
---

<div class="main-container">
  <div class="content-container">
    <h1 class="category-page__title">JAVA</h1>

    <div class="posts-grid">
      {% assign posts = site.categories["JAVA"] %}
      {% for post in posts %}
        {% include archive-single.html type="card" %}
      {% endfor %}
    </div>
  </div>
</div>
