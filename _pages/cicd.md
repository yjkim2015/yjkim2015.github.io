---
title: "CICD"
layout: default
permalink: /categories/cicd/
---

<div class="main-container">
  <div class="content-container">
    <h1 class="category-page__title">CICD</h1>

    {% assign posts = site.categories["CICD"] %}
    {% for post in posts %}
      {% include archive-single.html %}
    {% endfor %}
  </div>
</div>
