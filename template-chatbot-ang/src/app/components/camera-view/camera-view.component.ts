import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';

@Component({
  selector: 'app-camera-view',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './camera-view.component.html',
  styleUrls: ['./camera-view.component.css'],
})
export class CameraViewComponent {
  readonly backgrounds = {
    yard: this.makeBackground('yard.jpg'),
    patio: this.makeBackground('patio.jpg'),
    side: this.makeBackground('side.jpg'),
  };

  private makeBackground(image: string) {
    return {
      background: `url('assets/images/${image}') no-repeat center center / cover`,
    };
  }
}
