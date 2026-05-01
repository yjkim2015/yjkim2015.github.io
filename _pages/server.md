---
title: "SERVER"
layout: default
permalink: /categories/server/
---

<div class="main-container">
  <div class="content-container">
    <h1 class="category-page__title">SERVER</h1>

    {% assign posts = site.categories["SERVER"] %}
    {% for post in posts %}
      {% include archive-single.html %}
    {% endfor %}
  </div>
</div>
