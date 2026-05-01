---
title: "JPA"
layout: default
permalink: /categories/jpa/
---

<div class="main-container">
  <div class="content-container">
    <h1 class="category-page__title">JPA</h1>

    {% assign posts = site.categories["JPA"] %}
    {% for post in posts %}
      {% include archive-single.html %}
    {% endfor %}
  </div>
</div>
