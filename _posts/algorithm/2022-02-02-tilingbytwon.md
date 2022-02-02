---
title: 2 x n 타일링 by 백준 11726
categories:
- Algorithm
toc: true
toc_sticky: true
toc_label: 목차

---



 

##### 🔗 2 x n 타일링 백준 11726문제 

```java
package dynamic;

import java.util.Scanner;

public class TilingByTwon {

    public static int[] D;
    public static void main(String[] args) {


        Scanner sc = new Scanner(System.in);

        int n = sc.nextInt();

        D = new int[n+1];

        System.out.println(tiling(n));
    }

    public static int tiling(int n) {

        if (n < 3 ){
           return n;
        }

        if (D[n]> 0) {
            return D[n];
        }

        D[n] = tiling(  n-1) + tiling(n-2);

        return D[n] % 10007;
    }
}
```



<hr>


##### 💎결과 

![image-20220202150753115](../../assets/images/2022-02-02-tilingbytwon/image-20220202150753115.png)
