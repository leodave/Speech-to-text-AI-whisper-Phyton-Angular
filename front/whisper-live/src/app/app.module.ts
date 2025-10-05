import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { FormsModule } from '@angular/forms';
import { AppComponent } from './app.component'; // standalone: true

@NgModule({
  // ❌ declarations: [AppComponent],  // <-- remove this
  imports: [
    BrowserModule,
    FormsModule,
    AppComponent,            // <-- import the standalone component here
  ],
  bootstrap: [AppComponent],
})
export class AppModule {}
