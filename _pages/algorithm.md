---
title: "Algorithm"
layout: default
permalink: /categories/algorithm/
---

<div class="main-container">
  <div class="content-container">
    <h1 class="category-page__title">Algorithm</h1>

    {% assign posts = site.categories["Algorithm"] %}
    {% for post in posts %}
      {% include archive-single.html %}
    {% endfor %}
  </div>
</div>
