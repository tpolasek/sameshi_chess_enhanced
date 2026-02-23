#include <stdio.h>
#include <time.h>
#include "sameshi.h"

extern int b[120], bs, bd, root_depth;
extern int C(int s);

static const char* pc(int q){
    int a=j(q);
    if(!a)return "·";
    if(a==1)return q>0?"♙":"♟";
    if(a==2)return q>0?"♘":"♞";
    if(a==3)return q>0?"♗":"♝";
    if(a==4)return q>0?"♖":"♜";
    if(a==5)return q>0?"♕":"♛";
    return q>0?"♔":"♚";
}

static void board(void){
    puts("");
    printf("    a   b   c   d   e   f   g   h\n");
    printf("  ┌───┬───┬───┬───┬───┬───┬───┬───┐\n");
    for(int r=9;r>=2;r--){
        printf("%d │",r-1);
        for(int c=1;c<=8;c++){
            printf(" %s │",pc(b[r*10+c]));
        }
        printf(" %d\n",r-1);
        if(r>2)printf("  ├───┼───┼───┼───┼───┼───┼───┼───┤\n");
    }
    printf("  └───┴───┴───┴───┴───┴───┴───┴───┘\n");
    printf("    a   b   c   d   e   f   g   h\n");
}

static int sq(char f,char r){
    if(f<'a'||f>'h'||r<'1'||r>'8')return -1;
    return (r-'0'+1)*10+(f-'a'+1);
}

// Validate player's move (white = 1)
static int valid_move(int from, int to){
    int piece = b[from];

    // Must have a piece at source
    if(!piece || piece < 0) return 0;  // only white pieces

    // Save state
    int captured = b[to];

    // Make the move
    b[to] = piece;
    b[from] = 0;

    // Check if white's king is in check after the move
    int in_check = C(1);

    // Undo the move
    b[from] = piece;
    b[to] = captured;

    // Move is valid if it doesn't leave king in check
    return !in_check;
}

int main(void){
    I();
    char m[8];
    while(1){
        board();
        printf("move: ");
        if(scanf("%7s",m)!=1)break;
        if(m[0]=='q')break;
        int s=sq(m[0],m[1]),d=sq(m[2],m[3]);
        if(s<0||d<0)continue;
        if(!valid_move(s,d)){
            printf("Invalid move!\n");
            continue;
        }
        b[d]=b[s];
        b[s]=0;
        struct timespec t1,t2;
        clock_gettime(CLOCK_MONOTONIC,&t1);
        int bot_depth = 6;
        root_depth = bot_depth;
        S(-1,bot_depth,-30000,30000);
        clock_gettime(CLOCK_MONOTONIC,&t2);
        long ms=(t2.tv_sec-t1.tv_sec)*1000+(t2.tv_nsec-t1.tv_nsec)/1000000;
        printf("ai: %c%c%c%c (%ldms)\n",'a'+bs%10-1,'0'+bs/10-1,'a'+bd%10-1,'0'+bd/10-1,ms);
        b[bd]=b[bs];
        b[bs]=0;
    }
    return 0;
}
