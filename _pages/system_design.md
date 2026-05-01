---
title: "SYSTEM_DESIGN"
layout: default
permalink: /categories/system_design/
---

<div class="main-container">
  <div class="content-container">
    <h1 class="category-page__title">SYSTEM_DESIGN</h1>

    <div class="posts-grid">
      {% assign posts = site.categories["SYSTEM_DESIGN"] %}
      {% for post in posts %}
        {% include archive-single.html type="card" %}
      {% endfor %}
    </div>
  </div>
</div>
