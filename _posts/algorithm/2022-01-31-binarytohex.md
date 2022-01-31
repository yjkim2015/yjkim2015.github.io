---
title: 이진수 8진수 변환 by 백준 1373
categories:
- Algorithm
toc: true
toc_sticky: true
toc_label: 목차

---



 

##### 🔗 2진수 8진수 변환 백준 1373문제 

```java
package math;

import java.util.Scanner;

public class BinaryToHex {
    public static void main(String[] args) {

        Scanner sc = new Scanner(System.in);

        String num = sc.nextLine();

        if (num.length() % 3 == 1) {
            System.out.print(num.charAt(0));
        }
        else if (num.length() % 3 == 2) {

            System.out.print((num.charAt(0)-'0')* 2 + (num.charAt(1)-'0') );
        }

        for (int i = num.length()%3; i < num.length(); i+=3) {
            System.out.print((num.charAt(i)-'0')*4 + (num.charAt(i+1)-'0') * 2 + (num.charAt(i+2)-'0'));
        }
    }
}
```



<hr>


##### 💎결과 

![image-20220131122719716](../../assets/images/2022-01-31-binarytohex/image-20220131122719716.png)
