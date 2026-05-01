---
title: "SERVER"
layout: default
permalink: /categories/server/
---

<div class="main-container">
  <div class="content-container">
    <h1 class="category-page__title">SERVER</h1>

    <div class="posts-grid">
      {% assign posts = site.categories["SERVER"] %}
      {% for post in posts %}
        {% include archive-single.html type="card" %}
      {% endfor %}
    </div>
  </div>
</div>
