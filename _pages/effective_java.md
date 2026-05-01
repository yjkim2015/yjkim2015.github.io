---
title: "EFFECTIVE_JAVA"
layout: default
permalink: /categories/effective_java/
---

<div class="main-container">
  <div class="content-container">
    <h1 class="category-page__title">EFFECTIVE_JAVA</h1>

    <div class="posts-grid">
      {% assign posts = site.categories["EFFECTIVE_JAVA"] %}
      {% for post in posts %}
        {% include archive-single.html type="card" %}
      {% endfor %}
    </div>
  </div>
</div>
