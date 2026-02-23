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
    fflush(stdout);
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

    int type = j(piece);
    int dr = (to/10) - (from/10);
    int df = (to%10) - (from%10);
    int ad = dr < 0 ? -dr : dr;  // absolute delta row
    int af = df < 0 ? -df : df;  // absolute delta file

    // Check piece-specific movement rules
    if(type == 1){ // pawn
        int fwd = 10;
        // Forward move 1
        if(df == 0 && to == from + fwd && !b[to]) goto valid;
        // Forward move 2 from starting rank
        if(df == 0 && from < 40 && to == from + 2*fwd && !b[to] && !b[from+fwd]) goto valid;
        // Capture diagonally
        if(af == 1 && to == from + fwd + df && b[to] && b[to] < 0) goto valid;
        return 0;
    } else if(type == 2){ // knight - L-shaped moves
        int N[] = {-21, -19, -12, -8, 8, 12, 19, 21};
        int valid = 0;
        for(int i=0;i<8;i++) if(to == from + N[i]) valid = 1;
        if(!valid) return 0;
    } else if(type == 3){ // bishop - diagonal
        if(ad != af) return 0;
        // Check path is clear
        int step = (dr > 0 ? 1 : -1) * 10 + (df > 0 ? 1 : -1);
        for(int sq = from + step; sq != to; sq += step)
            if(b[sq]) return 0;
    } else if(type == 4){ // rook - orthogonal
        if(dr && df) return 0;
        // Check path is clear
        int step = dr ? (dr > 0 ? 10 : -10) : (df > 0 ? 1 : -1);
        for(int sq = from + step; sq != to; sq += step)
            if(b[sq]) return 0;
    } else if(type == 5){ // queen - diagonal or orthogonal
        if(dr && df && ad != af) return 0;
        // Check path is clear
        int step = 0;
        if(!dr) step = df > 0 ? 1 : -1;
        else if(!df) step = dr > 0 ? 10 : -10;
        else step = (dr > 0 ? 1 : -1) * 10 + (df > 0 ? 1 : -1);
        for(int sq = from + step; sq != to; sq += step)
            if(b[sq]) return 0;
    } else if(type == 6){ // king - one square any direction
        if(ad > 1 || af > 1) return 0;
    }

valid:
    // Check destination has own piece (can't capture own)
    if(b[to] > 0) return 0;

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
        fflush(stdout);
        if(scanf("%7s",m)!=1)break;
        if(m[0]=='q')break;
        int s=sq(m[0],m[1]),d=sq(m[2],m[3]);
        if(s<0||d<0)continue;
        if(!valid_move(s,d)){
            printf("Invalid move!\n");
            fflush(stdout);
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
        fflush(stdout);
        b[bd]=b[bs];
        b[bs]=0;
    }
    return 0;
}
