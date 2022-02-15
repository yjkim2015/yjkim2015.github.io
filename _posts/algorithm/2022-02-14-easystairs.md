---
title: 쉬운 계단수 by 백준 10844
categories:
- Algorithm
toc: true
toc_sticky: true
toc_label: 목차

---



 

##### 🔗 쉬운 계단 수 백준 10844문제 

```java
package dynamic;

import java.util.Scanner;

public class EasyStairs {

    public static final long MOD = 1000000000;

    public static long[][] stairs;

    public static void main(String[] args) {

        Scanner sc = new Scanner(System.in);

        int n = sc.nextInt();

        long result = 0;
        stairs = new long[n+1][10];

        for (int i = 1; i <=9; i++) {
            stairs[1][i] = 1;
        }

        for (int i = 2; i <= n; i++) {

            for (int j = 0; j <= 9; j++) {
                if (j-1 >= 0) {
                    stairs[i][j] += stairs[i-1][j-1];
                }

                if (j+1 <= 9) {
                    stairs[i][j] += stairs[i-1][j+1];
                }
                stairs[i][j] %= MOD;
            }
        }

        for (int i = 0; i <= 9; i++) {
            result += stairs[n][i];
        }
        System.out.println(result%MOD);
    }
}

```



<hr>


##### 💎결과 

![image-20220215132806629](../../assets/images/2022-02-14-easystairs/image-20220215132806629.png)
