---
title: 팩토리얼의 0의 개수 by 백준 1676
categories:
- Algorithm
toc: true
toc_sticky: true
toc_label: 목차

---



 

##### 🔗 팩토리얼의 0의 개수  백준 1676문제 

```java
package math;

import java.util.Scanner;

public class Factorial {
    public static void main(String[] args) {

        Scanner sc = new Scanner(System.in);

        int n = sc.nextInt();

        int count = 0;
        for(int i = 5; i <= n; i*=5) {
            count += n/i;
        }
        System.out.println(count);
    }
}

```



<hr>


##### 💎결과 

![image-20220130215748022](../../assets/images/2022-01-30-factorial/image-20220130215748022.png)
